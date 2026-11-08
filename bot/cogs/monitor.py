"""Мониторинг MC-сервера с устойчивыми уведомлениями и проверкой полноты списка игроков."""

import asyncio
import logging
import os
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer

from bot.utils.settings import SettingsStore

log = logging.getLogger(__name__)
CHECK_INTERVAL = 60


class Monitor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.was_online: bool | None = None
        self.went_down_at: datetime | None = None
        self.online_players: set[str] | None = None
        try:
            self.channel_id = max(0, int(os.getenv("MONITOR_CHANNEL", "0") or 0))
        except ValueError:
            log.error("MONITOR_CHANNEL должен быть числовым ID; мониторинг выключен")
            self.channel_id = 0

    async def cog_load(self) -> None:
        if self.channel_id or isinstance(
            getattr(self.bot, "settings", None), SettingsStore
        ):
            self.check_server.start()

    async def cog_unload(self) -> None:
        self.check_server.cancel()
        task = self.check_server.get_task()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    def _monitor_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(self.channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _channels(self) -> list[discord.TextChannel]:
        legacy = self._monitor_channel()
        store = getattr(self.bot, "settings", None)
        if not isinstance(store, SettingsStore):
            return [legacy] if legacy is not None else []
        rows = await store.all()
        overridden = {row["guild_id"] for row in rows}
        channels = (
            [legacy] if legacy is not None and legacy.guild.id not in overridden else []
        )
        for row in rows:
            if row["monitor_enabled"]:
                channel = self.bot.get_channel(row["monitor_channel_id"])
                if (
                    isinstance(channel, discord.TextChannel)
                    and channel.guild.id == row["guild_id"]
                ):
                    channels.append(channel)
        return channels

    async def _broadcast(self, channels: list[discord.TextChannel], **kwargs) -> None:
        for channel in channels:
            await self._send(channel, **kwargs)

    async def _ping(self) -> tuple[bool, str, set[str] | None]:
        try:
            async with asyncio.timeout(10):
                server = await JavaServer.async_lookup(
                    os.getenv("MC_SERVER", "localhost:25565"), timeout=3
                )
                status = await server.async_status(tries=1)
            players = status.players
            names = {p.name for p in players.sample} if players.sample else set()
            # Status API может отдавать случайную часть игроков. Такой список не годится для диффа.
            complete_names = names if len(names) == players.online else None
            return (
                True,
                f"{players.online}/{players.max} игроков, {round(status.latency)} мс",
                complete_names,
            )
        except Exception as error:  # noqa: BLE001 — mcstatus разбирает недоверенный ответ сервера
            log.debug("Проверка MC-сервера: %s", type(error).__name__)
            return False, "", None

    async def _send(self, channel: discord.TextChannel, **kwargs) -> None:
        try:
            await channel.send(
                **kwargs, allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.HTTPException as error:
            # Права или временный сбой Discord не должны останавливать фоновый цикл.
            log.warning(
                "Уведомление мониторинга в канал %s: HTTP %s", channel.id, error.status
            )

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_server(self) -> None:
        try:
            channels = await self._channels()
        except Exception as error:  # noqa: BLE001 — повторим чтение настроек в следующем цикле
            log.error("Настройки мониторинга: %s", type(error).__name__)
            return
        if not channels:
            self.was_online = None
            self.online_players = None
            return
        online, info, names = await self._ping()
        previous = self.was_online
        self.was_online = online

        if not online and previous is not False:
            self.went_down_at = datetime.now(UTC)
        if previous is None:
            self.online_players = names
            return

        if online and not previous:
            embed = discord.Embed(
                title="🟢 Сервер поднялся!",
                description=f"Заходите: `{os.getenv('MC_SERVER', 'localhost:25565')}`\n{info}",
                color=0x55FF55,
            )
            if self.went_down_at is not None:
                minutes = int(
                    (datetime.now(UTC) - self.went_down_at).total_seconds() // 60
                )
                embed.set_footer(text=f"Простой: {minutes} мин")
            self.went_down_at = None
            await self._broadcast(channels, embed=embed)
        elif not online and previous:
            await self._broadcast(
                channels,
                embed=discord.Embed(
                    title="🔴 Сервер упал",
                    description="Мониторинг продолжает наблюдение — сообщим, когда поднимется.",
                    color=0xFF5555,
                ),
            )
        elif online and names is not None and self.online_players is not None:
            changes = [
                *(
                    f"🟢 **{discord.utils.escape_markdown(name)}** зашёл на сервер"
                    for name in sorted(names - self.online_players)
                ),
                *(
                    f"🔴 **{discord.utils.escape_markdown(name)}** вышел с сервера"
                    for name in sorted(self.online_players - names)
                ),
            ]
            if changes:
                await self._broadcast(channels, content="\n".join(changes)[:2000])
        self.online_players = names if online else None

    @app_commands.command(
        name="мониторинг", description="Проверить состояние мониторинга MC-сервера"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        channels = await self._channels()
        channel = next(
            (item for item in channels if item.guild.id == interaction.guild_id), None
        )
        online, info, names = await self._ping()
        embed = discord.Embed(title="📡 Мониторинг сервера", color=0x5865F2)
        embed.add_field(
            name="Канал",
            value=channel.mention if channel else "Не настроен или недоступен",
            inline=False,
        )
        embed.add_field(
            name="Цикл",
            value="Работает" if self.check_server.is_running() else "Остановлен",
            inline=False,
        )
        embed.add_field(
            name="Сервер",
            value=f"🟢 Онлайн — {info}" if online else "🔴 Офлайн или недоступен",
            inline=False,
        )
        if names:
            embed.add_field(
                name="Игроки", value=", ".join(sorted(names))[:1024], inline=False
            )
        elif online and names is None:
            embed.add_field(
                name="Игроки",
                value="Сервер не передаёт полный список имён",
                inline=False,
            )
        embed.set_footer(text=f"Проверка каждые {CHECK_INTERVAL} сек")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @check_server.before_loop
    async def before_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Monitor(bot))
