"""Нейронка: команда /ai и ответы на упоминания."""

import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.ai import ROAST_COMEBACKS, ask_ai


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ai", description="Спросить нейронку")
    @app_commands.describe(вопрос="Любой вопрос, например: что такое редстоун?")
    async def ai(self, interaction: discord.Interaction, вопрос: str):
        await interaction.response.defer()
        try:
            await interaction.followup.send((await ask_ai(вопрос))[:2000])
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Ошибка нейронки: {type(e).__name__}: {e}")
            await interaction.followup.send("⚠️ Нейронка сейчас недоступна, попробуй позже.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Упомянули с текстом — отвечает нейронка; пустой пинг — посылает."""
        if message.author == self.bot.user:
            return
        if self.bot.user and self.bot.user.mentioned_in(message):
            text = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
            if text:  # задали вопрос — отвечает нейронка
                async with message.channel.typing():
                    try:
                        await message.reply((await ask_ai(text))[:2000])
                    except Exception as e:  # noqa: BLE001
                        print(f"⚠️ Ошибка нейронки: {type(e).__name__}: {e}")
                        await message.reply(random.choice(ROAST_COMEBACKS))  # бот никогда не пасует
            else:  # просто пинг — посылает
                await message.reply("Пошёл нахуй")
            return
        # префиксных команд нет — process_commands не нужен


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AI(bot))
