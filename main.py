"""Простой Discord-бот для майнкрафт-сервера — slash-команды."""

import os
import random
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # нужен для чтения упоминаний бота

bot = commands.Bot(command_prefix="!", intents=intents)  # префикс не используется

SYSTEM_PROMPT = (
    "Ты — полезный ассистент Discord-бота майнкрафт-сервера. "
    "Отвечай кратко, по делу, с лёгким юмором."
)


# ---------- нейронка ----------

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
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            },
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp,
    ):
        resp.raise_for_status()
        data = await resp.json()
        return data["choices"][0]["message"]["content"].strip()


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


async def ask_ai(question: str) -> str:
    """Сначала OpenRouter (ключ OPEN_ROUTER), иначе бесплатный Pollinations."""
    key = os.getenv("OPEN_ROUTER", "").strip()
    if key:
        try:
            return await ask_openrouter(key, question)
        except Exception as e:  # noqa: BLE001 — фолбэк, ловим всё
            print(f"⚠️ OPEN_ROUTER не сработал: {type(e).__name__}: {e}")
    return await ask_pollinations(question)  # последний шанс — бесплатный сервис


# ---------- события ----------

@bot.event
async def on_ready():
    # регистрация slash-команд на каждом сервере — работает мгновенно
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    print(f"✅ Бот запущен: {bot.user} (id={bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    """Упомянули с текстом — отвечает нейронка; пустой пинг — посылает."""
    if message.author == bot.user:
        return
    if bot.user and bot.user.mentioned_in(message):
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
    # префиксных команд нет — process_commands не нужен


# ---------- slash-команды ----------

@bot.tree.command(name="ping", description="Проверить задержку бота")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)} мс")


@bot.tree.command(name="hello", description="Поприветствовать бота")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Привет, {interaction.user.mention}!")


@bot.tree.command(name="roll", description="Кинуть кубик")
@app_commands.describe(грани="Сколько граней у кубика (по умолчанию 6)")
async def slash_roll(interaction: discord.Interaction, грани: app_commands.Range[int, 2, 1000] = 6):
    await interaction.response.send_message(
        f"🎲 {interaction.user.mention} выбросил(а) **{random.randint(1, грани)}** (d{грани})"
    )


@bot.tree.command(name="coin", description="Подбросить монетку")
async def slash_coin(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 {random.choice(['Орёл!', 'Решка!'])}")


@bot.tree.command(name="choose", description="Случайно выбрать из вариантов")
@app_commands.describe(варианты="Варианты через запятую: крипер, зомби, скелет")
async def slash_choose(interaction: discord.Interaction, варианты: str):
    options = [o.strip() for o in варианты.split(",") if o.strip()]
    if len(options) < 2:
        await interaction.response.send_message("Нужно минимум 2 варианта через запятую!", ephemeral=True)
        return
    await interaction.response.send_message(f"Я выбираю: **{random.choice(options)}**")


@bot.tree.command(name="server", description="Статус майнкрафт-сервера")
async def slash_server(interaction: discord.Interaction):
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


@bot.tree.command(name="ai", description="Спросить нейронку")
@app_commands.describe(вопрос="Любой вопрос, например: что такое редстоун?")
async def slash_ai(interaction: discord.Interaction, вопрос: str):
    await interaction.response.defer()
    try:
        await interaction.followup.send((await ask_ai(вопрос))[:2000])
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Ошибка нейронки: {type(e).__name__}: {e}")
        await interaction.followup.send("⚠️ Нейронка сейчас недоступна, попробуй позже.")


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise SystemExit("Задай токен: скопируй .env.example в .env и вставь DISCORD_TOKEN")

bot.run(token)


from aiohttp import web

async def handle_healthcheck(request):
    return web.Response(text="Бот работает!")

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Задай токен DISCORD_TOKEN в переменных окружения!")

    # Запускаем мини-сервер для хостинга (чтобы Render видел, что порт открыт)
    app_web = web.Application()
    app_web.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер для пинга запущен на порту {port}")

    # Запускаем самого Discord-бота
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
