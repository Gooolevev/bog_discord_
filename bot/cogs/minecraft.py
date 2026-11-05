"""Статус майнкрафт-сервера."""

import os

import discord
from discord import app_commands
from discord.ext import commands
from mcstatus import JavaServer


class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="server", description="Статус майнкрафт-сервера")
    async def server(self, interaction: discord.Interaction):
        address = os.getenv("MC_SERVER", "localhost:25565")
        await interaction.response.defer()
        try:
            server = await JavaServer.async_lookup(address)
            status = await server.async_status()
            players = status.players
            embed = discord.Embed(title=f"🟢 {address}", color=0x55FF55)
            embed.add_field(name="Игроки", value=f"{players.online}/{players.max}")
            embed.add_field(name="Версия", value=status.version.name)
            embed.add_field(name="Задержка", value=f"{round(status.latency)} мс")
            if players.sample:
                embed.add_field(name="Онлайн", value=", ".join(p.name for p in players.sample), inline=False)
            await interaction.followup.send(embed=embed)
        except Exception:  # noqa: BLE001 — mcstatus кидает разные типы ошибок
            await interaction.followup.send(f"🔴 Сервер `{address}` офлайн или недоступен.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minecraft(bot))
