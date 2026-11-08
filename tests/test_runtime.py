"""Запуск, повторное подключение и загрузка всех команд без Discord API."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

import main
from bot.utils.community import CommunityStore
from bot.utils.resources import ResourceStore
from bot.utils.settings import SettingsStore


def bot_mock(error=None):
    bot = MagicMock()
    bot.__aenter__ = AsyncMock(return_value=bot)
    bot.__aexit__ = AsyncMock(return_value=False)
    bot.start = AsyncMock(side_effect=error)
    bot.is_ready.return_value = True
    bot.is_closed.return_value = False
    return bot


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_creates_new_client_and_closes_old_one(self):
        first, second = bot_mock(OSError("offline")), bot_mock()
        with (
            patch.dict(os.environ, {"DISCORD_TOKEN": "test-token"}, clear=True),
            patch("main.load_dotenv"),
            patch("main.DiscordBot", side_effect=[first, second]) as factory,
            patch("main.asyncio.sleep", AsyncMock()) as sleep,
        ):
            await main.main()
        self.assertEqual(factory.call_count, 2)
        first.__aexit__.assert_awaited_once()
        second.__aexit__.assert_awaited_once()
        sleep.assert_awaited_once_with(5)

    async def test_invalid_token_is_not_retried(self):
        bot = bot_mock(discord.LoginFailure("Invalid token"))
        with (
            patch.dict(os.environ, {"DISCORD_TOKEN": "test-token"}, clear=True),
            patch("main.load_dotenv"),
            patch("main.DiscordBot", return_value=bot) as factory,
            patch("main.asyncio.sleep", AsyncMock()) as sleep,
            self.assertRaises(discord.LoginFailure),
        ):
            await main.main()
        self.assertEqual(factory.call_count, 1)
        sleep.assert_not_awaited()

    async def test_retry_limit_has_no_final_sleep(self):
        with (
            patch.dict(os.environ, {"DISCORD_TOKEN": "test-token"}, clear=True),
            patch("main.load_dotenv"),
            patch("main.CONNECT_ATTEMPTS", 3),
            patch(
                "main.DiscordBot", side_effect=lambda: bot_mock(OSError("offline"))
            ) as factory,
            patch("main.asyncio.sleep", AsyncMock()) as sleep,
            self.assertRaises(OSError),
        ):
            await main.main()
        self.assertEqual(factory.call_count, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_healthcheck_runs_with_bot_and_runner_is_cleaned_up(self):
        bot = bot_mock()
        runner = SimpleNamespace(setup=AsyncMock(), cleanup=AsyncMock())
        site = SimpleNamespace(start=AsyncMock())
        applications = []

        def app_runner(app):
            applications.append(app)
            return runner

        async def start(_token):
            route = next(iter(applications[0].router.routes()))
            result = await route.handler(MagicMock())
            self.assertEqual(result.status, 200)
            bot.is_ready.return_value = False
            self.assertEqual((await route.handler(MagicMock())).status, 503)

        bot.start.side_effect = start
        with (
            patch.dict(
                os.environ, {"DISCORD_TOKEN": "test-token", "PORT": "8080"}, clear=True
            ),
            patch("main.load_dotenv"),
            patch("main.DiscordBot", return_value=bot),
            patch("main.web.AppRunner", side_effect=app_runner),
            patch("main.web.TCPSite", return_value=site),
        ):
            await main.main()
        site.start.assert_awaited_once()
        runner.cleanup.assert_awaited_once()

    async def test_sync_is_not_repeated_on_reconnect(self):
        async with main.DiscordBot() as bot:
            guild = MagicMock(spec=discord.Guild, id=123)
            with (
                patch.object(bot.tree, "sync", AsyncMock()) as sync,
                patch.object(bot.tree, "copy_global_to"),
            ):
                await bot._sync_guild(guild)
                await bot._sync_guild(guild)
            sync.assert_awaited_once()

    async def test_all_cogs_and_commands_load_and_sessions_close(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ResourceStore(Path(temporary) / "builder.sqlite3")
            community_store = CommunityStore(Path(temporary) / "community.sqlite3")
            settings_store = SettingsStore(Path(temporary) / "community.sqlite3")
            with (
                patch.dict(os.environ, {"MONITOR_CHANNEL": "0"}),
                patch("bot.cogs.builder.ResourceStore", return_value=store),
                patch("main.SettingsStore", return_value=settings_store),
                patch(
                    "bot.utils.community.CommunityStore", return_value=community_store
                ),
            ):
                async with main.DiscordBot() as bot:
                    await bot.setup_hook()
                    # Загрузка расширения создаёт новый класс; берём его после setup_hook.
                    from bot.cogs.ai import AI

                    self.assertEqual(len(bot.cogs), 6)
                    commands = {
                        command.name: command.to_dict(bot.tree)
                        for command in bot.tree.get_commands()
                    }
                    self.assertEqual(len(commands), 18)
                    self.assertIn("сбор", commands)
                    self.assertTrue(bot.get_cog("Community").poll_view.is_persistent())
                    for name in ("построй", "ресет", "мониторинг"):
                        self.assertEqual(
                            int(commands[name]["default_member_permissions"]), 8
                        )
                    for name, limit in (
                        ("choose", 1900),
                        ("8ball", 1024),
                        ("poll", 4092),
                        ("ai", 2000),
                    ):
                        self.assertEqual(
                            commands[name]["options"][0]["max_length"], limit
                        )
                    ai_cog = bot.get_cog("AI")
                    assert isinstance(ai_cog, AI)
                    session = ai_cog.session
                self.assertTrue(session.closed)
                self.assertFalse(bot.extensions)
                self.assertFalse(
                    [
                        t
                        for t in asyncio.all_tasks()
                        if t is not asyncio.current_task() and not t.done()
                    ]
                )

    async def test_permission_errors_get_private_response(self):
        async with main.DiscordBot() as bot:
            request = MagicMock(spec=discord.Interaction)
            request.response.is_done.return_value = False
            request.response.send_message = AsyncMock()
            request.followup.send = AsyncMock()
            await bot.tree.on_error(
                request, discord.app_commands.MissingPermissions(["administrator"])
            )
            self.assertTrue(request.response.send_message.call_args.kwargs["ephemeral"])
            request.followup.send.assert_not_awaited()

    async def test_deferred_errors_use_followup_without_private_details(self):
        async with main.DiscordBot() as bot:
            request = MagicMock(spec=discord.Interaction, command="ai")
            request.response.is_done.return_value = True
            request.response.send_message = AsyncMock()
            request.followup.send = AsyncMock()
            error = discord.app_commands.CommandInvokeError(
                MagicMock(), ValueError("PRIVATE_QUESTION")
            )
            with self.assertLogs("main", level="ERROR") as logs:
                await bot.tree.on_error(request, error)
            self.assertNotIn("PRIVATE_QUESTION", "\n".join(logs.output))
            self.assertTrue(request.followup.send.call_args.kwargs["ephemeral"])
            request.response.send_message.assert_not_awaited()
