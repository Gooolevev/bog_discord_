"""Регрессии AI: HTTP-ошибки, приватность запросов и ограничение нагрузки."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
from discord.ext import commands

from bot.cogs.ai import AI
from bot.utils.ai import ROAST_COMEBACKS, AIError, PollinationsClient, ask_ai


def response(status=200, content: str | None = "Готово", *, data=None, headers=None):
    result = MagicMock()
    result.status = status
    result.headers = headers or {}
    result.json = AsyncMock(
        return_value=data
        if data is not None
        else {
            "choices": [{"message": {"content": content}}],
        }
    )
    result.__aenter__ = AsyncMock(return_value=result)
    result.__aexit__ = AsyncMock(return_value=False)
    return result


class AITests(unittest.IsolatedAsyncioTestCase):
    def client(self, *responses) -> tuple[PollinationsClient, MagicMock]:
        session = MagicMock(spec=aiohttp.ClientSession)
        session.post.side_effect = responses
        return PollinationsClient(session, "test-key"), session

    async def test_post_separates_instructions_and_limits_output(self):
        client, session = self.client(response(content="x" * 3000))
        self.assertEqual(len(await ask_ai("Вопрос пользователя", client)), 2000)
        args, kwargs = session.post.call_args
        self.assertNotIn("Вопрос пользователя", args[0])
        messages = kwargs["json"]["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertEqual(messages[1]["content"], "Вопрос пользователя")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")

    async def test_missing_key_does_not_send_request(self):
        session = MagicMock()
        with self.assertRaises(AIError):
            await PollinationsClient(session, "").ask("Вопрос")
        session.post.assert_not_called()

    async def test_permanent_errors_are_not_retried(self):
        for status in (400, 401, 402, 403, 404):
            with (
                self.subTest(status=status),
                patch("bot.utils.ai.asyncio.sleep", AsyncMock()) as sleep,
            ):
                client, session = self.client(response(status))
                with self.assertRaises(AIError):
                    await client.ask("Вопрос")
                self.assertEqual(session.post.call_count, 1)
                sleep.assert_not_awaited()

    async def test_temporary_errors_retry_then_succeed(self):
        client, session = self.client(response(500), response(503), response())
        with patch("bot.utils.ai.asyncio.sleep", AsyncMock()) as sleep:
            self.assertEqual(await client.ask("Вопрос"), "Готово")
        self.assertEqual(session.post.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.await_args_list], [1, 2])

    async def test_network_error_logs_hide_request_details(self):
        private = "PRIVATE_QUESTION_AND_KEY"
        client, session = self.client(*(aiohttp.ClientError(private) for _ in range(3)))
        with (
            patch("bot.utils.ai.asyncio.sleep", AsyncMock()) as sleep,
            self.assertLogs("bot.utils.ai") as logs,
            self.assertRaises(AIError) as error,
        ):
            await client.ask("Вопрос")
        self.assertNotIn(private, str(error.exception))
        self.assertNotIn(private, "\n".join(logs.output))
        self.assertEqual(sleep.await_count, 2)
        self.assertEqual(session.post.call_count, 3)

    async def test_invalid_and_empty_responses(self):
        for result in (
            response(content=" "),
            response(content=None),
            response(data={}),
            response(data=[]),
        ):
            with self.subTest(response=result):
                client, session = self.client(result)
                with self.assertRaises(AIError):
                    await client.ask("Вопрос")
                self.assertEqual(session.post.call_count, 1)

    async def test_cooldown_blocks_extra_requests(self):
        client, session = self.client(response())
        await client.ask("Первый")
        with self.assertRaisesRegex(AIError, "через"):
            await client.ask("Второй")
        self.assertEqual(session.post.call_count, 1)

    async def test_rate_limit_is_bounded(self):
        for delay in ("999999", "не число"):
            client, session = self.client(response(429, headers={"Retry-After": delay}))
            with self.assertRaises(AIError):
                await client.ask("Вопрос")
            self.assertLessEqual(
                client._next_request_at - asyncio.get_running_loop().time(), 300
            )
            self.assertEqual(session.post.call_count, 1)

    async def test_concurrent_request_is_rejected_and_cancellation_releases_lock(self):
        entered = asyncio.Event()
        blocked = asyncio.Event()
        result = response()

        async def wait_for_response():
            entered.set()
            await blocked.wait()

        result.json.side_effect = wait_for_response
        client, session = self.client(result)
        task = asyncio.create_task(client.ask("Первый"))
        try:
            await asyncio.wait_for(entered.wait(), timeout=1)
            with self.assertRaisesRegex(AIError, "другой вопрос"):
                await client.ask("Второй")
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(client._lock.locked())
        self.assertEqual(session.post.call_count, 1)

    async def test_validation_and_local_answers_do_not_use_api(self):
        client = MagicMock(ask=AsyncMock(return_value="i can build a house"))
        for question in ("", " ", "x" * 2001):
            with self.assertRaises(AIError):
                await ask_ai(question, client)
        self.assertIn(await ask_ai("ты клоун", client), ROAST_COMEBACKS)
        client.ask.assert_not_awaited()
        self.assertEqual(
            await ask_ai("почему плохо работает редстоун", client),
            "i can build a house",
        )

    async def test_provider_refusal_is_not_replaced_with_a_taunt(self):
        answer = "Извините, не могу помочь с этим. Могу предложить безопасный вариант."
        client = MagicMock(ask=AsyncMock(return_value=answer))
        self.assertEqual(await ask_ai("Вопрос", client), answer)


class AIListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_bare_mention_opens_a_friendly_entry_point_without_api(self):
        bot = MagicMock(spec=commands.Bot, user=MagicMock(id=123))
        cog = AI(bot)
        cog._answer = AsyncMock()
        message = MagicMock(spec=discord.Message)
        message.author.bot = False
        message.mentions = [bot.user]
        message.content = "<@123>"
        message.reply = AsyncMock()
        await cog.on_message(message)
        cog._answer.assert_not_awaited()
        self.assertIn("/hello", message.reply.call_args.args[0])

    async def test_other_bots_and_everyone_mentions_do_not_trigger_ai(self):
        bot = MagicMock(
            spec=commands.Bot, user=MagicMock(spec=discord.ClientUser, id=123)
        )
        cog = AI(bot)
        cog._answer = AsyncMock()
        for author_is_bot, mentions in ((True, [bot.user]), (False, [])):
            message = MagicMock(
                spec=discord.Message,
                author=MagicMock(spec=discord.User, bot=author_is_bot),
                mentions=mentions,
            )
            await cog.on_message(message)
        cog._answer.assert_not_awaited()

    async def test_direct_mention_replies_without_pinging_users(self):
        bot = MagicMock(
            spec=commands.Bot, user=MagicMock(spec=discord.ClientUser, id=123)
        )
        cog = AI(bot)
        cog._answer = AsyncMock(return_value="Ответ @everyone")
        message = MagicMock(spec=discord.Message)
        message.author.bot = False
        message.mentions = [bot.user]
        message.content = "<@123> Вопрос"
        message.reply = AsyncMock()
        await cog.on_message(message)
        cog._answer.assert_awaited_once_with("Вопрос")
        self.assertEqual(
            message.reply.call_args.kwargs["allowed_mentions"].to_dict(),
            discord.AllowedMentions.none().to_dict(),
        )
