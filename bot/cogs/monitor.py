"""Автомониторинг майнкрафт-сервера: оповещения о падении, подъёме и игроках."""

import os
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer

CHECK_INTERVAL = 60  # секунд между проверками


class Monitor(commands.Cog):
    """Следит за MC-сервером: статус + кто зашёл/вышел."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.was_online: bool | None = None  # None = ещё не проверяли
        self.went_down_at: datetime | None = None
        self.online_players: set[str] = set()  # ники с прошлой проверки
        self.channel_id = int(os.getenv("MONITOR_CHANNEL", "0") or 0)

    async def cog_load(self) -> None:
        if self.channel_id:
            self.check_server.start()

    async def cog_unload(self) -> None:
        self.check_server.cancel()

    def _monitor_channel(self) -> discord.TextChannel | None:
        return self.bot.get_channel(self.channel_id)  # type: ignore[return-value]

    async def _ping(self) -> tuple[bool, str, set[str]]:
        """(онлайн, описание, ники игроков). Любая ошибка = сервер недоступен."""
        address = os.getenv("MC_SERVER", "localhost:25565")
        try:
            server = await JavaServer.async_lookup(address)
            status = await server.async_status()
            info = f"{status.players.online}/{status.players.max} игроков, {round(status.latency)} мс"
            names = {p.name for p in status.players.sample} if status.players.sample else set()
            return True, info, names
        except Exception:  # noqa: BLE001 — любая ошибка = сервер недоступен
            return False, "", set()

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_server(self) -> None:
        channel = self._monitor_channel()
        if channel is None:
            return

        online, info, names = await self._ping()

        # первый запуск — просто фиксируем состояние, без сообщений
        if self.was_online is None:
            self.was_online = online
            self.online_players = names
            if not online:
                self.went_down_at = datetime.now(UTC)
            return

        if online and not self.was_online:
            embed = discord.Embed(
                title="🟢 Сервер поднялся!",
                description=f"Заходите: `{os.getenv('MC_SERVER', 'localhost:25565')}`\n{info}",
                color=0x55FF55,
            )
            if self.went_down_at is not None:
                downtime = datetime.now(UTC) - self.went_down_at
                embed.set_footer(text=f"Простой: {int(downtime.total_seconds() // 60)} мин")
                self.went_down_at = None
            await channel.send(embed=embed)
            self.online_players = names

        elif not online and self.was_online:
            self.went_down_at = datetime.now(UTC)
            embed = discord.Embed(
                title="🔴 Сервер упал",
                description="Мониторинг продолжает наблюдение — сообщим, когда поднимется.",
                color=0xFF5555,
            )
            await channel.send(embed=embed)

        elif online and names != self.online_players:
            # дифф ников: кто зашёл, кто вышел
            for name in sorted(names - self.online_players):
                await channel.send(f"🟢 **{name}** зашёл на сервер")
            for name in sorted(self.online_players - names):
                await channel.send(f"🔴 **{name}** вышел с сервера")
            self.online_players = names

        self.was_online = online

    @app_commands.command(name="мониторинг", description="Проверить состояние мониторинга MC-сервера")
    async def status(self, interaction: discord.Interaction):
        """Диагностика: куда пишем, что видит бот прямо сейчас."""
        await interaction.response.defer(ephemeral=True)  # пинг может идти секунд 10
        channel = self._monitor_channel()
        online, info, names = await self._ping()

        embed = discord.Embed(title="📡 Мониторинг сервера", color=0x5865F2)
        embed.add_field(
            name="Канал",
            value=channel.mention if channel else f"❌ не найден (ID `{self.channel_id}`)",
            inline=False,
        )
        embed.add_field(
            name="Сервер",
            value=f"🟢 Онлайн — {info}" if online else "🔴 Офлайн или недоступен",
            inline=False,
        )
        if names:
            embed.add_field(name="Игроки", value=", ".join(sorted(names)), inline=False)
        embed.set_footer(text=f"Проверка каждые {CHECK_INTERVAL} сек")
        await interaction.followup.send(embed=embed)

    @check_server.before_loop
    async def before_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Monitor(bot))
