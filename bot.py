"""Простой Discord-бот — проверка, что всё работает."""

import os
import random
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # включить на портале разработчика!

bot = commands.Bot(command_prefix="!", intents=intents)


async def ask_pollinations(question: str) -> str:
    """Спросить бесплатную нейронку (Pollinations.ai, без ключа)."""
    url = f"https://text.pollinations.ai/{quote(question)}"
    last_error: Exception = RuntimeError("pollinations не ответил")
    for _attempt in range(3):  # сервис бесплатный, бывают сбои — пробуем 3 раза
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp,
            ):
                resp.raise_for_status()
                return (await resp.text()).strip()
        except Exception as e:  # noqa: BLE001 — любой сбой сети повторяем
            last_error = e
    raise last_error


async def ask_openrouter(key: str, question: str) -> str:
    """Спросить OpenRouter (бесплатные модели, ключ OPEN_ROUTER)."""
    async with (
        aiohttp.ClientSession() as session,
        session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
                "messages": [
                    {"role": "system", "content": "Ты — полезный ассистент Discord-бота майнкрафт-сервера. Отвечай кратко, по делу, с лёгким юмором."},
                    {"role": "user", "content": question},
                ],
            },
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp,
    ):
        resp.raise_for_status()
        data = await resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def ask_ai(question: str) -> str:
    """Сначала OpenRouter (ключ OPEN_ROUTER), иначе бесплатный Pollinations."""
    key = os.getenv("OPEN_ROUTER", "").strip()
    if key:
        try:
            return await ask_openrouter(key, question)
        except Exception as e:  # noqa: BLE001 — фолбэк, ловим всё
            print(f"⚠️ OPEN_ROUTER не сработал: {type(e).__name__}: {e}")
    return await ask_pollinations(question)  # последний шанс — бесплатный сервис


@bot.event
async def on_ready():
    print(f"✅ Бот запущен: {bot.user} (id={bot.user.id})")


@bot.command()
async def ping(ctx):
    """Проверка задержки."""
    await ctx.send(f"Pong! {round(bot.latency * 1000)} мс")


@bot.event
async def on_message(message):
    """Отвечать на упоминания бота."""
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        # текст без самого упоминания
        text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if text:  # задали вопрос — отвечает нейронка
            async with message.channel.typing():
                try:
                    await message.reply((await ask_ai(text))[:2000])
                except Exception as e:  # noqa: BLE001
                    print(f"⚠️ Ошибка нейронки: {type(e).__name__}: {e}")
                    await message.reply("⚠️ Нейронка сейчас недоступна, попробуй позже.")
        else:  # просто пинг — посылает
            await message.reply("Пошёл нахуй")
        return
    await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    """Поприветствовать бота."""
    await ctx.send(f"Привет, {ctx.author.mention}!")


@bot.command()
async def roll(ctx, sides: int = 6):
    """Кинуть кубик: !roll или !roll 20."""
    if not 2 <= sides <= 1000:
        await ctx.send("Кубик от 2 до 1000 граней!")
        return
    await ctx.send(f"🎲 {ctx.author.mention} выбросил(а) **{random.randint(1, sides)}** (d{sides})")


@bot.command()
async def coin(ctx):
    """Подбросить монетку: !coin."""
    await ctx.send(f"🪙 {random.choice(['Орёл!', 'Решка!'])}")


@bot.command()
async def choose(ctx, *, variants: str):
    """Случайный выбор: !choose крипер, зомби, скелет."""
    options = [o.strip() for o in variants.split(",") if o.strip()]
    if len(options) < 2:
        await ctx.send("Нужно минимум 2 варианта через запятую!")
        return
    await ctx.send(f"Я выбираю: **{random.choice(options)}**")


@bot.command()
async def server(ctx):
    """Статус майнкрафт-сервера: !server."""
    address = os.getenv("MC_SERVER", "localhost:25565")
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
        await ctx.send(embed=embed)
    except Exception:  # noqa: BLE001 — mcstatus кидает разные типы ошибок
        await ctx.send(f"🔴 Сервер `{address}` офлайн или недоступен.")


@bot.command(name="AI", aliases=["нейро", "спроси"])
async def ai(ctx, *, question: str):
    """Спросить нейронку: !ai что такое редстоун?"""
    async with ctx.typing():
        try:
            await ctx.reply((await ask_ai(question))[:2000])
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Ошибка нейронки: {type(e).__name__}: {e}")
            await ctx.send("⚠️ Нейронка сейчас недоступна, попробуй позже.")


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise SystemExit("Задай токен: скопируй .env.example в .env и вставь DISCORD_TOKEN")

bot.run(token)
