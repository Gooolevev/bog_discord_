"""Нейронка: команда /ai и ответы на прямые упоминания."""

import logging
import os

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.ai import MAX_QUESTION_LENGTH, AIError, PollinationsClient, ask_ai
from bot.utils.ui import card

log = logging.getLogger(__name__)


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()
        self.client = PollinationsClient(
            self.session,
            os.getenv("POLLINATIONS_API_KEY", ""),
            os.getenv("POLLINATIONS_MODEL", "openai"),
        )

    async def cog_unload(self) -> None:
        await self.session.close()

    async def _answer(self, question: str) -> str:
        try:
            return await ask_ai(question, self.client)
        except AIError as error:
            return str(error)
        except Exception as error:  # noqa: BLE001 — изоляция внешнего API без приватных данных в логах
            log.error("Неожиданная ошибка AI: %s", type(error).__name__)
            return "⚠️ Нейронка сейчас недоступна, попробуй позже."

    @app_commands.command(name="ai", description="Спросить нейронку")
    @app_commands.describe(вопрос="Любой вопрос, например: что такое редстоун?")
    async def ai(
        self,
        interaction: discord.Interaction,
        вопрос: app_commands.Range[str, 1, MAX_QUESTION_LENGTH],
    ) -> None:
        await interaction.response.defer()
        await interaction.followup.send(
            embed=card("ПОМОЩНИК · Ответ", await self._answer(вопрос)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.bot.user is None:
            return
        # mentioned_in также реагирует на @everyone; здесь нужен именно прямой пинг.
        if self.bot.user not in message.mentions:
            return
        text = (
            message.content.replace(f"<@{self.bot.user.id}>", "")
            .replace(f"<@!{self.bot.user.id}>", "")
            .strip()
        )
        try:
            if text:
                async with message.channel.typing():
                    answer = await self._answer(text)
            else:
                answer = "Привет! Открой /hello — там опросы, сбор команды и Minecraft. Или задай вопрос после упоминания."
            await message.reply(answer, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException as error:
            log.warning("Не удалось ответить на упоминание: HTTP %s", error.status)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AI(bot))
