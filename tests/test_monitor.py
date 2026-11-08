"""Регрессии мониторинга: отказ Discord и неполные списки игроков."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord

from bot.cogs.monitor import Monitor


class MonitorTests(unittest.IsolatedAsyncioTestCase):
    def monitor(self):
        with patch.dict("os.environ", {"MONITOR_CHANNEL": "0"}):
            return Monitor(MagicMock())

    async def test_send_failure_does_not_kill_loop(self):
        monitor = self.monitor()
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 42
        channel.send = AsyncMock(
            side_effect=[
                discord.Forbidden(
                    MagicMock(
                        spec=aiohttp.ClientResponse, status=403, reason="Forbidden"
                    ),
                    "Нет прав",
                ),
                None,
            ]
        )
        monitor._monitor_channel = lambda: channel
        monitor._ping = AsyncMock(
            side_effect=[(False, "", None), (True, "0/20", set())]
        )
        monitor.was_online = True
        monitor.check_server.before_loop(AsyncMock())
        monitor.check_server.change_interval(seconds=0)
        monitor.check_server.count = 2
        with self.assertLogs("bot.cogs.monitor", level="WARNING"):
            await monitor.check_server.start()
        self.assertFalse(monitor.check_server.failed())
        self.assertTrue(monitor.was_online)
        self.assertEqual(channel.send.await_count, 2)

    async def test_partial_player_sample_is_not_treated_as_departures(self):
        monitor = self.monitor()
        channel = MagicMock(spec=discord.TextChannel, send=AsyncMock())
        monitor._monitor_channel = lambda: channel
        monitor.was_online = True
        monitor.online_players = {"Alex", "Steve"}
        monitor._ping = AsyncMock(
            side_effect=[
                (True, "2/20", None),
                (True, "2/20", {"Alex", "Steve"}),
                (True, "1/20", {"Alex"}),
            ]
        )
        await monitor.check_server()
        await monitor.check_server()
        channel.send.assert_not_awaited()
        await monitor.check_server()
        self.assertEqual(channel.send.await_count, 1)
        self.assertIn("Steve", channel.send.call_args.kwargs["content"])

    async def test_ping_marks_incomplete_samples(self):
        monitor = self.monitor()
        server = SimpleNamespace(
            async_status=AsyncMock(
                return_value=SimpleNamespace(
                    players=SimpleNamespace(
                        online=10, max=20, sample=[SimpleNamespace(name="Alex")]
                    ),
                    latency=12,
                )
            )
        )
        with patch(
            "bot.cogs.monitor.JavaServer.async_lookup", AsyncMock(return_value=server)
        ):
            online, _, names = await monitor._ping()
        self.assertTrue(online)
        self.assertIsNone(names)
        server.async_status.assert_awaited_once_with(tries=1)

    async def test_invalid_channel_config_disables_monitor_only(self):
        with (
            patch.dict("os.environ", {"MONITOR_CHANNEL": "oops"}),
            self.assertLogs("bot.cogs.monitor"),
        ):
            monitor = Monitor(MagicMock())
        self.assertEqual(monitor.channel_id, 0)
        await monitor.cog_load()
        self.assertFalse(monitor.check_server.is_running())

    async def test_non_text_channels_are_ignored(self):
        monitor = self.monitor()
        with patch.object(
            monitor.bot,
            "get_channel",
            return_value=MagicMock(spec=discord.VoiceChannel),
        ):
            self.assertIsNone(monitor._monitor_channel())
