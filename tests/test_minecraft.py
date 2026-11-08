"""Кэш, конкурентные запросы и отказ Minecraft без сети."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from bot.cogs.minecraft import Minecraft, ServerView


class MinecraftTests(unittest.IsolatedAsyncioTestCase):
    def cog(self):
        with patch.dict("os.environ", {"MC_SERVER": "localhost:25565"}):
            return Minecraft(MagicMock())

    async def test_simultaneous_queries_share_cache_and_sanitize_mc_text(self):
        cog = self.cog()
        server = SimpleNamespace(
            async_status=AsyncMock(
                return_value=SimpleNamespace(
                    players=SimpleNamespace(
                        online=10,
                        max=20,
                        sample=[SimpleNamespace(name="§aAlex_*@everyone")],
                    ),
                    version=SimpleNamespace(name="§bPaper"),
                    latency=12.5,
                )
            )
        )
        with patch(
            "bot.cogs.minecraft.JavaServer.async_lookup", AsyncMock(return_value=server)
        ) as lookup:
            results = await asyncio.gather(*(cog.status_embed() for _ in range(6)))
        lookup.assert_awaited_once()
        server.async_status.assert_awaited_once_with(tries=1)
        self.assertIn("Можно заходить", results[0].title)
        self.assertNotIn("§", str(results[0].to_dict()))
        self.assertNotIn("@everyone", str(results[0].to_dict()))
        results[0].title = "Изменено"
        self.assertNotEqual(results[1].title, "Изменено")

    async def test_timeout_returns_useful_panel_and_caches_failure(self):
        cog = self.cog()
        with (
            patch(
                "bot.cogs.minecraft.JavaServer.async_lookup",
                AsyncMock(side_effect=TimeoutError),
            ) as lookup,
            self.assertLogs("bot.cogs.minecraft", level="WARNING"),
        ):
            embed = await cog.status_embed()
            await cog.status_embed()
        lookup.assert_awaited_once()
        self.assertIn("Нет ответа", embed.title)
        self.assertTrue(any("localhost:25565" in field.value for field in embed.fields))

    async def test_refresh_cooldown_prevents_duplicate_edits(self):
        cog = self.cog()
        cog.status_embed = AsyncMock(return_value=MagicMock())
        view = ServerView(cog)
        self.addCleanup(view.stop)
        request = MagicMock()
        request.response.defer = AsyncMock()
        request.response.is_done.return_value = True
        request.edit_original_response = AsyncMock()
        request.followup.send = AsyncMock()
        await view.refresh.callback(request)
        await view.refresh.callback(request)
        cog.status_embed.assert_awaited_once()
        request.edit_original_response.assert_awaited_once()
        self.assertTrue(request.followup.send.call_args.kwargs["ephemeral"])

    async def test_unload_stops_live_panels(self):
        cog = self.cog()
        view = ServerView(cog)
        self.addCleanup(view.stop)
        cog._views.add(view)
        await cog.cog_unload()
        self.assertTrue(view.is_finished())
        self.assertFalse(cog._views)
