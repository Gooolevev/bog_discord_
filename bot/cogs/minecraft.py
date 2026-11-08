"""Панель Minecraft: статус, обновление и инструкция подключения."""

import asyncio
import logging
import os
import re
import time
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands
from mcstatus import JavaServer

from bot.utils.ui import SUCCESS, WARNING, SafeView, card, plain, private

log = logging.getLogger(__name__)


def mc_text(value: str, limit: int = 200) -> str:
    return plain(re.sub(r"§.", "", value), limit)


class ServerView(SafeView):
    def __init__(self, cog: "Minecraft") -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.next_refresh = 0.0

    @discord.ui.button(
        label="Обновить статус", emoji="🔄", style=discord.ButtonStyle.primary
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        now = time.monotonic()
        if now < self.next_refresh:
            await private(interaction, "Статус только что обновлён. Подожди 10 секунд.")
            return
        self.next_refresh = now + 10
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=await self.cog.status_embed(), view=self
        )

    @discord.ui.button(
        label="Как подключиться", emoji="🔗", style=discord.ButtonStyle.secondary
    )
    async def connect(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = card(
            "MINECRAFT · Подключение",
            "**Java Edition**\nОткрой «Сетевая игра» → «Добавить сервер» и вставь адрес ниже.",
        )
        embed.add_field(
            name="Адрес сервера",
            value=f"`{self.cog.address.replace('`', '')[:200]}`",
            inline=False,
        )
        embed.add_field(
            name="Не пускает?",
            value="Проверь версию игры и список модов у организатора сервера.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.address = (
            os.getenv("MC_SERVER", "localhost:25565").strip() or "localhost:25565"
        )
        self._query_lock = asyncio.Lock()
        self._cached: discord.Embed | None = None
        self._cached_until = 0.0
        self._views: set[ServerView] = set()

    async def cog_unload(self) -> None:
        for view in self._views:
            view.stop()
        self._views.clear()

    async def status_embed(self) -> discord.Embed:
        async with self._query_lock:
            if self._cached is not None and time.monotonic() < self._cached_until:
                return self._cached.copy()
            try:
                async with asyncio.timeout(10):
                    server = await JavaServer.async_lookup(self.address, timeout=3)
                    status = await server.async_status(tries=1)
            except Exception as error:  # noqa: BLE001 — недоверенный ответ MC-сервера
                log.warning("Запрос статуса MC-сервера: %s", type(error).__name__)
                embed = card(
                    "MINECRAFT · Нет ответа",
                    "Сервер выключен или временно недоступен.\nМожно проверить снова кнопкой ниже.",
                    color=WARNING,
                )
            else:
                players = status.players
                embed = card(
                    "MINECRAFT · Можно заходить",
                    "Мир на месте. Не хватает только вашей команды.",
                    color=SUCCESS,
                )
                embed.add_field(
                    name="Игроки", value=f"**{players.online}** / {players.max}"
                )
                embed.add_field(
                    name="Версия", value=mc_text(status.version.name) or "Неизвестно"
                )
                embed.add_field(name="Отклик", value=f"{round(status.latency)} мс")
                if players.sample:
                    embed.add_field(
                        name="Игроки в ответе сервера",
                        value=" · ".join(
                            mc_text(player.name, 40) for player in players.sample[:20]
                        )[:1024]
                        or "Нет имён",
                        inline=False,
                    )
                    embed.add_field(
                        name="Важно",
                        value="Сервер может показывать только часть игроков.",
                        inline=False,
                    )
            embed.add_field(
                name="Адрес Java Edition",
                value=f"`{self.address.replace('`', '')[:200]}`",
                inline=False,
            )
            embed.timestamp = datetime.now(UTC)
            embed.set_footer(text="MINECRAFT • кэш 20 сек. • панель активна 5 минут")
            self._cached = embed
            self._cached_until = time.monotonic() + 20
            return embed.copy()

    async def show(
        self, interaction: discord.Interaction, *, ephemeral: bool = False
    ) -> None:
        await interaction.response.defer(ephemeral=ephemeral)
        view = ServerView(self)
        self._views = {item for item in self._views if not item.is_finished()}
        self._views.add(view)
        view.message = await interaction.followup.send(
            embed=await self.status_embed(), view=view, ephemeral=ephemeral, wait=True
        )

    @app_commands.command(
        name="server", description="Панель Minecraft: игроки, статус и подключение"
    )
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def server(self, interaction: discord.Interaction) -> None:
        await self.show(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minecraft(bot))
