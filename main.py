"""Запуск бота и необязательной HTTP-проверки готовности для хостинга."""

import asyncio
import logging
import os

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bot.dashboard import create_dashboard_app
from bot.utils.settings import SettingsStore

log = logging.getLogger(__name__)
COGS = (
    "bot.cogs.general",
    "bot.cogs.community",
    "bot.cogs.minecraft",
    "bot.cogs.ai",
    "bot.cogs.builder",
    "bot.cogs.monitor",
)
CONNECT_ATTEMPTS = 5


class CommandTree(app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "❌ Недостаточно прав для этой команды."
        elif isinstance(error, app_commands.BotMissingPermissions):
            message = "❌ Боту не хватает прав для этой команды."
        elif isinstance(error, app_commands.NoPrivateMessage):
            message = "❌ Команда работает только на сервере."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"⏳ Повтори через {error.retry_after:.0f} сек."
        else:
            original = getattr(error, "original", error)
            log.error("Команда %s: %s", interaction.command, type(original).__name__)
            message = (
                "⚠️ Не удалось выполнить команду. Операция могла завершиться частично."
            )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException as send_error:
            log.warning(
                "Не удалось отправить ошибку команды: HTTP %s", send_error.status
            )


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            tree_cls=CommandTree,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self._synced_guilds: set[int] = set()
        self.settings = SettingsStore()
        self._dashboard_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        await self.settings.initialize()
        for module in COGS:
            await self.load_extension(module)
            log.info("Ког загружен: %s", module)
        if port := os.getenv("BOT_API_PORT", "").strip():
            number = int(port)
            if not 1 <= number <= 65535:
                raise ValueError("BOT_API_PORT должен быть в диапазоне 1–65535")
            app = create_dashboard_app(self, os.getenv("BOT_API_SECRET", ""))
            self._dashboard_runner = web.AppRunner(app, access_log=None)
            await self._dashboard_runner.setup()
            await web.TCPSite(self._dashboard_runner, "127.0.0.1", number).start()
            log.info("Закрытый API панели запущен на loopback:%s", number)

    async def close(self) -> None:
        if self._dashboard_runner is not None:
            await self._dashboard_runner.cleanup()
            self._dashboard_runner = None
        await super().close()

    async def _sync_guild(self, guild: discord.Guild) -> None:
        if guild.id in self._synced_guilds:
            return
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        except discord.HTTPException as error:
            log.warning(
                "Синхронизация команд сервера %s: HTTP %s", guild.id, error.status
            )
        else:
            self._synced_guilds.add(guild.id)

    async def on_ready(self) -> None:
        for guild in self.guilds:
            await self._sync_guild(guild)
        log.info("Бот готов: %s", self.user)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._sync_guild(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        self._synced_guilds.discard(guild.id)


async def main() -> None:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("Задай DISCORD_TOKEN в .env или окружении")

    bot: DiscordBot | None = None
    runner: web.AppRunner | None = None

    async def healthcheck(request: web.Request) -> web.Response:
        ready = bot is not None and bot.is_ready() and not bot.is_closed()
        return web.Response(
            text="Бот готов" if ready else "Бот подключается",
            status=200 if ready else 503,
        )

    try:
        if port_value := os.getenv("PORT"):
            port = int(port_value)
            if not 1 <= port <= 65535:
                raise ValueError("PORT должен быть в диапазоне 1–65535")
            app = web.Application()
            app.router.add_get("/", healthcheck)
            runner = web.AppRunner(app)
            await runner.setup()
            await web.TCPSite(runner, "0.0.0.0", port).start()
            log.info("HTTP-проверка готовности запущена на порту %s", port)

        for attempt in range(CONNECT_ATTEMPTS):
            try:
                # После сбоя нужен новый клиент с новыми сессиями и задачами.
                async with DiscordBot() as bot:
                    await bot.start(token)
                return
            except (
                aiohttp.ClientError,
                OSError,
                discord.GatewayNotFound,
                discord.ConnectionClosed,
                discord.HTTPException,
            ) as error:
                if (
                    isinstance(error, discord.HTTPException)
                    and error.status < 500
                    and error.status != 429
                ):
                    raise
                if attempt == CONNECT_ATTEMPTS - 1:
                    raise
                delay = min(5 * 2**attempt, 60)
                log.warning(
                    "Подключение: %s; повтор через %s сек.", type(error).__name__, delay
                )
                await asyncio.sleep(delay)
    finally:
        if runner is not None:
            await runner.cleanup()


def run() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен")
    except discord.LoginFailure:
        raise SystemExit("Неверный DISCORD_TOKEN") from None
    except discord.PrivilegedIntentsRequired:
        raise SystemExit(
            "Включи Message Content Intent и Server Members Intent в Developer Portal"
        ) from None
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except Exception as error:  # noqa: BLE001 — граница приложения, без утечки деталей запроса
        log.error("Запуск завершился ошибкой: %s", type(error).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    run()
