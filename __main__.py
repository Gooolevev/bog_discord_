"""Точка входа: создаём бота, грузим коги, подключаемся с ретраями."""

import asyncio
import os
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # нужен для чтения упоминаний бота
intents.members = True  # нужен для /random_user (полный список участников)

bot = commands.Bot(command_prefix="!", intents=intents)  # префикс не используется

COGS = [
    "bot.cogs.general",
    "bot.cogs.minecraft",
    "bot.cogs.ai",
    "bot.cogs.builder",
    "bot.cogs.monitor",
]


@bot.event
async def on_ready():
    # регистрация slash-команд на каждом сервере — работает мгновенно
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    print(f"✅ Бот запущен: {bot.user} (id={bot.user.id})")


async def main() -> None:
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"📦 Ког загружен: {cog}")
        await bot.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Задай токен: в .env вставь DISCORD_TOKEN")
    # сеть может резать gateway Discord'а — подключаемся до победного
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен. До встречи!")
            break  # Ctrl+C — чистый выход без простыни traceback
        except Exception as e:  # noqa: BLE001 — любой сбой подключения повторяем
            print(f"⚠️ Подключение не удалось ({type(e).__name__}), повтор через 10 сек...")
            time.sleep(10)
