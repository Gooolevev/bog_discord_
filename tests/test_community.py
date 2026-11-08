"""Голосования, гонки за места, перезапуск и сбои интерфейса без Discord API."""

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from bot.cogs.community import Community, PublishModal, VoteView, board_embed
from bot.cogs.general import HomeView
from bot.utils.community import BoardError, CommunityStore, poll_options
from bot.utils.ui import SafeView


def interaction(user_id=2, guild_id=10, message_id=30):
    request = MagicMock(spec=discord.Interaction)
    request.user.id = user_id
    request.guild_id = guild_id
    request.channel_id = 20
    request.message.id = message_id
    request.permissions = discord.Permissions(send_messages=True)
    request.app_permissions = discord.Permissions(send_messages=True, embed_links=True)
    request.response.defer = AsyncMock()
    request.response.send_message = AsyncMock()
    request.response.edit_message = AsyncMock()
    request.response.send_modal = AsyncMock()
    request.response.is_done.return_value = True
    request.edit_original_response = AsyncMock()
    request.followup.send = AsyncMock()
    return request


class CommunityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = CommunityStore(Path(self.temporary.name) / "community.sqlite3")
        await self.store.initialize()

    async def board(self, kind="poll", **kwargs):
        parameters = {
            "guild_id": 10,
            "channel_id": 20,
            "author_id": 1,
            "kind": kind,
            "title": "Куда отправимся?",
            "options": ["В шахту", "В порт"],
            "capacity": 2,
            "minutes": 60,
        }
        parameters.update(kwargs)
        board = await self.store.create(**parameters)
        await self.store.attach(board, 30)
        return await self.store.get(board.id, board.guild_id)

    async def test_poll_vote_change_withdraw_and_cooldown(self):
        board = await self.board()
        start = time.time()
        with patch("bot.utils.community.time.time", return_value=start):
            result = await self.store.act(board.id, 10, 2, 0)
            self.assertEqual(result.votes, {2: 0})
            with self.assertRaisesRegex(BoardError, "уже сохранён"):
                await self.store.act(board.id, 10, 2, 0)
            with self.assertRaisesRegex(BoardError, "2 секунды"):
                await self.store.act(board.id, 10, 2, 1)
        with patch("bot.utils.community.time.time", return_value=start + 3):
            result = await self.store.act(board.id, 10, 2, 1)
            self.assertEqual(result.votes, {2: 1})
        with patch("bot.utils.community.time.time", return_value=start + 6):
            result = await self.store.act(board.id, 10, 2, -1)
            self.assertEqual(result.votes, {})
            with self.assertRaises(BoardError):
                await self.store.act(board.id, 10, 2, 0)

    async def test_concurrent_signups_never_exceed_capacity(self):
        board = await self.board("party")
        results = await asyncio.gather(
            *(self.store.act(board.id, 10, user, 0) for user in range(2, 12)),
            return_exceptions=True,
        )
        self.assertEqual(sum(not isinstance(value, Exception) for value in results), 1)
        self.assertTrue(
            all(
                isinstance(value, BoardError)
                for value in results
                if isinstance(value, Exception)
            )
        )
        stored = await self.store.get(board.id, 10)
        self.assertEqual(len(stored.votes), 2)
        winner = next(user for user in stored.votes if user != 1)
        with patch("bot.utils.community.time.time", return_value=time.time() + 3):
            await self.store.act(board.id, 10, winner, -1)
            result = await self.store.act(board.id, 10, 99, 0)
        self.assertEqual(set(result.votes), {1, 99})

    async def test_restart_guild_isolation_and_message_identity(self):
        board = await self.board()
        await self.store.act(board.id, 10, 2, 0)
        restarted = CommunityStore(self.store.path)
        await restarted.initialize()
        result = await restarted.for_message(10, 30)
        self.assertEqual(result.votes, {2: 0})
        for operation in (
            restarted.get(board.id, 11),
            restarted.for_message(11, 30),
            restarted.act(board.id, 11, 2, 1),
            restarted.for_message(10, 31),
        ):
            with self.assertRaises(BoardError):
                await operation

    async def test_close_permissions_and_closed_card_rejects_votes(self):
        board = await self.board()
        with self.assertRaises(BoardError):
            await self.store.act(board.id, 10, 2, -1, close=True)
        result = await self.store.act(board.id, 10, 2, -1, close=True, moderator=True)
        self.assertTrue(result.closed)
        with self.assertRaises(BoardError):
            await self.store.act(board.id, 10, 3, 0)
        self.assertEqual(len(await self.store.due()), 1)
        await self.store.published(result)
        self.assertEqual(await self.store.due(), [])

    async def test_deadline_rejects_votes_and_is_restored_after_restart(self):
        board = await self.board()
        with patch("bot.utils.community.time.time", return_value=board.ends_at):
            with self.assertRaises(BoardError):
                await self.store.act(board.id, 10, 2, 0)
            restarted = CommunityStore(self.store.path)
            await restarted.initialize()
            self.assertEqual([item.id for item in await restarted.due()], [board.id])

    async def test_validation_and_creation_spam_limit(self):
        for text in (
            "a",
            "a; A",
            "a;;b",
            ";b",
            "a;" + "x" * 81,
            ";".join(map(str, range(7))),
        ):
            with self.subTest(text=text), self.assertRaises(BoardError):
                poll_options(text)
        self.assertEqual(poll_options(None), ["За", "Против"])
        for overrides in (
            {"minutes": 0},
            {"minutes": 1441},
            {"title": " "},
            {"kind": "party", "capacity": 1},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(BoardError):
                await self.board(**overrides)
        board = await self.board()
        for choice in (-2, 2):
            with self.assertRaises(BoardError):
                await self.store.act(board.id, 10, 2, choice)
        with self.assertRaisesRegex(BoardError, "15 секунд"):
            await self.store.create(10, 20, 1, "poll", "Новый", ["Да", "Нет"], 0, 60)

    async def test_embed_limits_and_tie_result(self):
        board = await self.board(
            title="*" * 4092, options=["*" * 79 + str(i) for i in range(6)]
        )
        board.votes = {index + 2: index for index in range(6)}
        board.closed = True
        embed = board_embed(board)
        self.assertLessEqual(len(embed), 6000)
        self.assertLessEqual(len(embed.description), 4096)
        self.assertTrue(any("Ничья" in field.value for field in embed.fields))
        for field in embed.fields:
            self.assertLessEqual(len(field.name), 256)
            self.assertLessEqual(len(field.value), 1024)
        board.kind = "party"
        board.capacity = 50
        board.title = "Большая стройка"
        board.votes = {9999999999999999999 - index: 0 for index in range(50)}
        party_embed = board_embed(board)
        for field in party_embed.fields:
            self.assertLessEqual(len(field.value), 1024)

    async def test_active_limit_is_per_guild_and_persists_without_cooldown_bypass(self):
        for user_id in range(1, 21):
            await self.store.create(
                10, 20, user_id, "poll", "Вопрос", ["Да", "Нет"], 0, 60
            )
        with self.assertRaisesRegex(BoardError, "20 активных"):
            await self.store.create(10, 20, 21, "poll", "Вопрос", ["Да", "Нет"], 0, 60)
        await self.store.create(11, 20, 21, "poll", "Вопрос", ["Да", "Нет"], 0, 60)

    def cog(self):
        cog = Community(MagicMock())
        cog.store = self.store
        cog.render = AsyncMock()
        self.addCleanup(cog.poll_view.stop)
        self.addCleanup(cog.party_view.stop)
        return cog

    async def test_ui_uses_database_permissions_and_stale_click_is_private(self):
        board = await self.board()
        cog = self.cog()
        request = interaction()
        await cog.action(request, close=True)
        self.assertIn("Завершить", request.followup.send.call_args.args[0])
        cog.render.assert_not_awaited()
        await self.store.act(board.id, 10, 1, -1, close=True)
        await cog.action(request, 0)
        self.assertTrue(request.followup.send.call_args.kwargs["ephemeral"])
        self.assertIn("завершена", request.followup.send.call_args.args[0])

    async def test_vote_select_commits_and_updates_original_board(self):
        board = await self.board()
        cog = self.cog()
        view = VoteView(cog, board, 2)
        self.addCleanup(view.stop)
        request = interaction()
        await view.submit(request, 1)
        self.assertEqual((await self.store.get(board.id, 10)).votes, {2: 1})
        cog.render.assert_awaited_once()
        request.edit_original_response.assert_awaited_once()
        self.assertTrue(view.is_finished())

    async def test_publish_checks_permissions_and_cleans_failed_publication(self):
        cog = self.cog()
        request = interaction()
        request.app_permissions.embed_links = False
        await cog.publish(request, "poll", "Вопрос?")
        self.assertIn("права", request.followup.send.call_args.args[0])
        request.app_permissions.embed_links = True
        cog.bot.get_partial_messageable.return_value.send = AsyncMock(
            side_effect=OSError("offline")
        )
        with self.assertRaises(OSError):
            await cog.publish(request, "poll", "Вопрос?")
        # Неудачная публикация не занимает слот и не запускает cooldown.
        await self.store.create(10, 20, 2, "poll", "Повтор", ["Да", "Нет"], 0, 60)

    async def test_publish_attaches_bot_message_and_keeps_confirmation_private(self):
        cog = self.cog()
        request = interaction()
        message = MagicMock(id=30, jump_url="https://discord.com/channels/10/20/30")
        channel = cog.bot.get_partial_messageable.return_value
        channel.send = AsyncMock(return_value=message)
        await cog.publish(request, "party", "Общая стройка", capacity=4, minutes=30)
        board = await self.store.for_message(10, 30)
        self.assertEqual(board.capacity, 4)
        self.assertEqual(board.votes, {2: 0})
        self.assertTrue(request.followup.send.call_args.kwargs["ephemeral"])
        self.assertEqual(
            channel.send.call_args.kwargs["allowed_mentions"].to_dict(),
            discord.AllowedMentions.none().to_dict(),
        )

    async def test_saved_vote_can_be_recovered_when_discord_edit_fails(self):
        board = await self.board()
        cog = self.cog()
        cog.render.side_effect = discord.HTTPException(
            MagicMock(status=503, reason="Unavailable"), "Сбой"
        )
        request = interaction()
        with self.assertRaises(discord.HTTPException):
            await cog.action(request, 0)
        self.assertEqual((await self.store.get(board.id, 10)).votes, {2: 0})
        cog.render.side_effect = None
        await cog.action(request)
        self.assertEqual(cog.render.await_count, 2)

    async def test_expiry_recovers_from_http_error_and_retries(self):
        board = await self.board()
        await self.store.act(board.id, 10, 1, -1, close=True)
        cog = self.cog()
        cog.render.side_effect = discord.Forbidden(
            MagicMock(status=403, reason="Forbidden"), "Нет прав"
        )
        with self.assertLogs("bot.cogs.community", level="WARNING"):
            await cog.expire()
        self.assertEqual(len(await self.store.due()), 1)
        cog.render.side_effect = None
        await cog.expire()
        self.assertEqual(cog.render.await_count, 2)

    async def test_persistent_views_timeout_and_personal_menu(self):
        cog = self.cog()
        self.assertTrue(cog.poll_view.is_persistent())
        self.assertTrue(cog.party_view.is_persistent())
        view = HomeView(MagicMock(), 1)
        self.addCleanup(view.stop)
        request = interaction(user_id=2)
        self.assertFalse(await view.interaction_check(request))
        self.assertTrue(request.followup.send.call_args.kwargs["ephemeral"])
        for kind in ("poll", "party"):
            modal = PublishModal(cog, kind)
            self.addCleanup(modal.stop)
            self.assertEqual(len(modal.children), 3)
        timed = SafeView(timeout=1)
        self.addCleanup(timed.stop)
        timed.add_item(discord.ui.Button(label="Тест"))
        timed.message = MagicMock(edit=AsyncMock())
        await timed.on_timeout()
        self.assertTrue(timed.children[0].disabled)
        timed.message.edit.assert_awaited_once()

    async def test_unload_stops_private_vote_menus(self):
        board = await self.board()
        cog = self.cog()
        view = VoteView(cog, board, 2)
        self.addCleanup(view.stop)
        cog._vote_views.add(view)
        await cog.cog_unload()
        self.assertTrue(view.is_finished())
        self.assertFalse(cog._vote_views)
