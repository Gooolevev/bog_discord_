"""Закрытый API панели, права и применение настроек без реального Discord."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from aiohttp.test_utils import TestClient, TestServer

from bot.cogs.community import Community
from bot.cogs.monitor import Monitor
from bot.dashboard import create_dashboard_app
from bot.utils.settings import SettingsStore

GUILD = 123456789012345678
USER = 223456789012345678
CHANNEL = 323456789012345678
SECRET = "test-only-internal-secret-for-local-tests"


class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = SettingsStore(Path(self.temporary.name) / "community.sqlite3")
        await self.store.initialize()
        self.channel = MagicMock(spec=discord.TextChannel)
        self.channel.id = CHANNEL
        self.channel.name = "новости-сервера"
        self.channel.permissions_for.return_value = discord.Permissions(
            view_channel=True, send_messages=True, embed_links=True
        )
        self.guild = SimpleNamespace(
            id=GUILD,
            owner_id=999,
            name="Тестовый сервер",
            icon=None,
            member_count=7,
            me=MagicMock(),
            text_channels=[self.channel],
            fetch_member=AsyncMock(
                return_value=SimpleNamespace(roles=[SimpleNamespace(id=42)])
            ),
            fetch_roles=AsyncMock(
                return_value=[
                    SimpleNamespace(id=GUILD, permissions=discord.Permissions.none()),
                    SimpleNamespace(
                        id=42, permissions=discord.Permissions(manage_guild=True)
                    ),
                ]
            ),
            get_channel=lambda value: self.channel if value == CHANNEL else None,
        )
        self.channel.guild = self.guild
        self.bot = MagicMock()
        self.bot.settings = self.store
        self.bot.is_ready.return_value = True
        self.bot.is_closed.return_value = False
        self.bot.latency = 0.05
        self.bot.get_guild.side_effect = lambda value: (
            self.guild if value == GUILD else None
        )
        self.bot.fetch_guild = AsyncMock(return_value=self.guild)
        self.bot.get_cog.return_value = None
        self.client = TestClient(TestServer(create_dashboard_app(self.bot, SECRET)))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    def headers(self):
        return {"Authorization": f"Bearer {SECRET}"}

    def url(self):
        return f"/guilds/{GUILD}?user_id={USER}"

    async def test_secret_and_bot_readiness_are_required(self):
        self.assertEqual((await self.client.get(self.url())).status, 401)
        self.bot.is_ready.return_value = False
        response = await self.client.get(self.url(), headers=self.headers())
        self.assertEqual(response.status, 503)
        self.bot.fetch_guild.assert_not_awaited()

    async def test_settings_save_restart_and_read(self):
        body = {
            "monitor_enabled": True,
            "monitor_channel_id": str(CHANNEL),
            "poll_minutes": 120,
        }
        response = await self.client.put(self.url(), json=body, headers=self.headers())
        self.assertEqual(response.status, 200)
        restarted = SettingsStore(self.store.path)
        await restarted.initialize()
        self.assertEqual((await restarted.get(GUILD))["poll_minutes"], 120)
        response = await self.client.get(self.url(), headers=self.headers())
        data = await response.json()
        self.assertEqual(data["settings"]["monitor_channel_id"], str(CHANNEL))
        self.assertEqual(data["guild"]["name"], self.guild.name)
        self.assertEqual(data["bot"]["latency_ms"], 50)
        self.assertEqual((await self.store.get(GUILD + 1))["poll_minutes"], 60)

    async def test_permissions_are_fresh_on_every_action(self):
        response = await self.client.get(self.url(), headers=self.headers())
        self.assertEqual(response.status, 200)
        self.guild.fetch_roles.return_value = [
            SimpleNamespace(id=42, permissions=discord.Permissions.none())
        ]
        response = await self.client.put(
            self.url(),
            json={
                "monitor_enabled": False,
                "monitor_channel_id": "0",
                "poll_minutes": 30,
            },
            headers=self.headers(),
        )
        self.assertEqual(response.status, 403)
        self.assertEqual((await self.store.get(GUILD))["poll_minutes"], 60)
        self.assertEqual(self.guild.fetch_member.await_count, 2)

    async def test_list_only_returns_installed_managed_guilds(self):
        response = await self.client.post(
            "/guilds",
            json={"user_id": str(USER), "guild_ids": [str(GUILD), str(GUILD + 1)]},
            headers=self.headers(),
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(
            [g["id"] for g in (await response.json())["guilds"]], [str(GUILD)]
        )

    async def test_foreign_channel_and_invalid_settings_are_rejected(self):
        for body in (
            {
                "monitor_enabled": True,
                "monitor_channel_id": str(CHANNEL + 1),
                "poll_minutes": 60,
            },
            {"monitor_enabled": True, "monitor_channel_id": "0", "poll_minutes": 60},
            {"monitor_enabled": False, "monitor_channel_id": "0", "poll_minutes": True},
            {"monitor_enabled": False, "monitor_channel_id": "0", "poll_minutes": 1441},
            {
                "monitor_enabled": False,
                "monitor_channel_id": "0",
                "poll_minutes": 60,
                "extra": 1,
            },
        ):
            with self.subTest(body=body):
                response = await self.client.put(
                    self.url(), json=body, headers=self.headers()
                )
                self.assertEqual(response.status, 400)
        self.channel.permissions_for.return_value = discord.Permissions.none()
        response = await self.client.put(
            self.url(),
            json={
                "monitor_enabled": True,
                "monitor_channel_id": str(CHANNEL),
                "poll_minutes": 60,
            },
            headers=self.headers(),
        )
        self.assertEqual(response.status, 400)

    async def test_poll_default_and_monitor_channels_use_saved_settings(self):
        await self.store.save(GUILD, True, CHANNEL, 90)
        community = Community(self.bot)
        self.addCleanup(community.poll_view.stop)
        self.addCleanup(community.party_view.stop)
        self.assertEqual(await community.poll_minutes(GUILD), 90)
        with patch.dict("os.environ", {"MONITOR_CHANNEL": "0"}):
            monitor = Monitor(self.bot)
        self.bot.get_channel.return_value = self.channel
        self.assertEqual(await monitor._channels(), [self.channel])
        await self.store.save(GUILD, False, CHANNEL, 90)
        monitor.channel_id = CHANNEL
        self.assertEqual(await monitor._channels(), [])

    async def test_json_errors_and_missing_members_do_not_leak_details(self):
        response = await self.client.put(
            self.url(), data="not-json", headers=self.headers()
        )
        self.assertEqual(response.status, 400)
        self.guild.fetch_member.side_effect = discord.NotFound(
            MagicMock(status=404, reason="not found"), "PRIVATE_MEMBER_DETAILS"
        )
        response = await self.client.get(self.url(), headers=self.headers())
        self.assertEqual(response.status, 404)
        self.assertNotIn("PRIVATE_MEMBER_DETAILS", await response.text())
