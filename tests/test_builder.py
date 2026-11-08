"""Проверки владения объектами, безопасного удаления и повторной постройки."""

import asyncio
import tempfile
import unittest
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord

from bot.cogs.builder import (
    Builder,
    CategoryConfig,
    ForumChannelConfig,
    RoleConfig,
    TextChannelConfig,
    VoiceChannelConfig,
)
from bot.utils.resources import ResourceStore


def channel(
    resource_id,
    name,
    *,
    category=None,
    kind: type[discord.abc.GuildChannel] = discord.TextChannel,
) -> MagicMock:
    result = MagicMock(spec=kind)
    result.id = resource_id
    result.name = name
    result.category_id = category.id if category else None
    result.delete = AsyncMock()
    result.mention = f"<#{resource_id}>"
    return result


def interaction(guild, current) -> MagicMock:
    return MagicMock(
        spec=discord.Interaction,
        guild=guild,
        channel=current,
        channel_id=current.id,
        response=MagicMock(
            spec=discord.InteractionResponse,
            defer=AsyncMock(),
            send_message=AsyncMock(),
        ),
        followup=MagicMock(spec=discord.Webhook, send=AsyncMock()),
    )


async def reset(
    builder: Builder, request: discord.Interaction, *, confirm: bool = False
) -> None:
    # Callback команды Cog вызывается с явным self; у discord.py также есть вариант без Cog.
    callback = cast(
        Callable[[Builder, discord.Interaction, bool, bool, bool], Awaitable[None]],
        builder.reset.callback,
    )
    await callback(builder, request, True, True, confirm)


class BuilderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ResourceStore(Path(self.tmp.name) / "builder.sqlite3")
        await self.store.initialize()
        self.builder = Builder(MagicMock(), self.store)
        self.pause = patch("bot.cogs.builder.asyncio.sleep", AsyncMock())
        self.pause.start()
        self.addCleanup(self.pause.stop)

    async def test_store_survives_restart_and_is_scoped_to_guild(self):
        await self.store.add(1, 100)
        await self.store.add(1, 100)
        await self.store.add(2, 200)
        reopened = ResourceStore(self.store.path)
        await reopened.initialize()
        self.assertEqual(await reopened.ids(1), {100})
        await reopened.remove(1, 100)
        self.assertEqual(await reopened.ids(1), set())
        self.assertEqual(await reopened.ids(2), {200})

    async def test_reset_only_deletes_owned_resources_and_preserves_populated_category(
        self,
    ):
        current = channel(1, "команды")
        manual = channel(2, "ручной-канал")
        owned = channel(3, "переименованный-канал-бота")
        category = channel(4, "категория-бота", kind=discord.CategoryChannel)
        category.channels = [manual]
        current.category_id = None
        role = MagicMock(spec=discord.Role)
        role.id, role.name, role.managed = 5, "Роль", False
        role.is_default.return_value = False
        role.__lt__.return_value = True
        role.delete = AsyncMock()
        manual_role = MagicMock(spec=discord.Role)
        manual_role.id, manual_role.name = 6, "Роль"
        manual_role.delete = AsyncMock()
        guild = MagicMock(
            spec=discord.Guild,
            id=10,
            channels=[current, manual, owned, category],
            roles=[role, manual_role],
            me=MagicMock(),
        )
        for resource in (owned, category, role):
            await self.store.add(guild.id, resource.id)
        request = interaction(guild, current)
        await reset(self.builder, request, confirm=True)
        owned.delete.assert_awaited_once()
        role.delete.assert_awaited_once()
        for resource in (current, manual, category, manual_role):
            resource.delete.assert_not_awaited()
        self.assertEqual(await self.store.ids(guild.id), {category.id})

    async def test_reset_requires_explicit_confirmation(self):
        current, owned = channel(1, "команды"), channel(2, "бот")
        guild = MagicMock(
            spec=discord.Guild, id=10, channels=[current, owned], roles=[], me=None
        )
        await self.store.add(guild.id, owned.id)
        await reset(self.builder, interaction(guild, current))
        owned.delete.assert_not_awaited()
        self.assertEqual(await self.store.ids(guild.id), {owned.id})

    async def test_reset_preserves_current_channel_and_its_category(self):
        category = channel(2, "категория", kind=discord.CategoryChannel)
        current = channel(1, "команды", category=category)
        category.channels = [current]
        guild = MagicMock(
            spec=discord.Guild, id=10, channels=[current, category], roles=[], me=None
        )
        for resource in (current, category):
            await self.store.add(guild.id, resource.id)
        await reset(self.builder, interaction(guild, current), confirm=True)
        current.delete.assert_not_awaited()
        category.delete.assert_not_awaited()

    async def test_failed_deletion_remains_tracked(self):
        owned = channel(2, "бот")
        owned.delete.side_effect = discord.Forbidden(
            MagicMock(spec=aiohttp.ClientResponse, status=403, reason="Forbidden"),
            "Нет прав",
        )
        await self.store.add(10, owned.id)
        with self.assertLogs("bot.cogs.builder", level="WARNING"):
            self.assertFalse(await self.builder._delete(10, owned))
        self.assertEqual(await self.store.ids(10), {owned.id})

    def guild_with_category(self, *, community=False):
        category = channel(20, "категория", kind=discord.CategoryChannel)
        category.text_channels, category.forums = [], []
        category.stage_channels, category.voice_channels = [], []
        category.overwrites = {}
        guild = MagicMock(
            spec=discord.Guild,
            id=10,
            name="Тест",
            roles=[],
            categories=[category],
            channels=[category],
            text_channels=[],
            features=["COMMUNITY"] if community else [],
            me=None,
            bitrate_limit=96000,
            edit=AsyncMock(),
            create_forum=AsyncMock(),
            create_stage_channel=AsyncMock(),
        )

        def create(name, **kwargs):
            resource = channel(
                100 + len(guild.channels),
                name,
                category=category,
                kind=kwargs.pop("kind"),
            )
            guild.channels.append(resource)
            if isinstance(resource, discord.TextChannel):
                category.text_channels.append(resource)
                guild.text_channels.append(resource)
            else:
                category.voice_channels.append(resource)
            return resource

        guild.create_text_channel = AsyncMock(
            side_effect=lambda name, **kw: create(name, kind=discord.TextChannel, **kw)
        )
        guild.create_voice_channel = AsyncMock(
            side_effect=lambda name, **kw: create(name, kind=discord.VoiceChannel, **kw)
        )
        return guild, category

    async def test_rebuild_reuses_fallback_channels_and_tracks_new_ids(self):
        guild, category = self.guild_with_category()
        cfg = CategoryConfig(
            name=category.name,
            forum_channels=[ForumChannelConfig("форум", "тема")],
            voice_channels=[VoiceChannelConfig("сцена", is_stage=True)],
        )
        request = interaction(guild, channel(1, "команды"))
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", []),
            patch("bot.cogs.builder.SERVER_STRUCTURE", [cfg]),
        ):
            await self.builder._build(request, "обычный", False)
            await self.builder._build(request, "обычный", False)
        guild.create_text_channel.assert_awaited_once()
        guild.create_voice_channel.assert_awaited_once()
        guild.create_forum.assert_not_awaited()
        guild.create_stage_channel.assert_not_awaited()
        self.assertEqual(
            await self.store.ids(guild.id),
            {ch.id for ch in guild.channels if ch != category},
        )

    async def test_existing_stage_does_not_create_regular_voice(self):
        guild, category = self.guild_with_category(community=True)
        category.stage_channels.append(channel(30, "сцена", kind=discord.StageChannel))
        category.text_channels.append(channel(31, "форум"))
        cfg = CategoryConfig(
            name=category.name,
            forum_channels=[ForumChannelConfig("форум", "тема")],
            voice_channels=[VoiceChannelConfig("сцена", is_stage=True)],
        )
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", []),
            patch("bot.cogs.builder.SERVER_STRUCTURE", [cfg]),
        ):
            await self.builder._build(
                interaction(guild, channel(1, "команды")), "обычный", False
            )
        guild.create_voice_channel.assert_not_awaited()
        guild.create_text_channel.assert_not_awaited()
        self.assertEqual(await self.store.ids(guild.id), set())

    async def test_clean_preserves_untracked_orphan_channels(self):
        guild, _ = self.guild_with_category()
        manual = channel(3, "ручной")
        owned = channel(4, "создан-ботом")
        guild.text_channels = [manual, owned]
        await self.store.add(guild.id, owned.id)
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", []),
            patch("bot.cogs.builder.SERVER_STRUCTURE", []),
        ):
            await self.builder._build(
                interaction(guild, channel(1, "команды")), "обычный", True
            )
        manual.delete.assert_not_awaited()
        owned.delete.assert_awaited_once()

    async def test_existing_afk_channel_is_configured(self):
        guild, category = self.guild_with_category()
        afk = channel(30, "afk", kind=discord.VoiceChannel)
        category.voice_channels.append(afk)
        cfg = CategoryConfig(
            name=category.name, voice_channels=[VoiceChannelConfig("afk", is_afk=True)]
        )
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", []),
            patch("bot.cogs.builder.SERVER_STRUCTURE", [cfg]),
        ):
            await self.builder._build(
                interaction(guild, channel(1, "команды")), "обычный", False
            )
        self.assertEqual(guild.edit.call_args.kwargs["afk_channel"], afk)

    async def test_new_channels_preserve_category_access_rules(self):
        guild, category = self.guild_with_category()
        restricted_role = MagicMock(spec=discord.Role)
        restriction = discord.PermissionOverwrite(view_channel=False)
        category.overwrites = {restricted_role: restriction}
        cfg = CategoryConfig(
            name=category.name, text_channels=[TextChannelConfig("чат")]
        )
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", []),
            patch("bot.cogs.builder.SERVER_STRUCTURE", [cfg]),
        ):
            await self.builder._build(
                interaction(guild, channel(1, "команды")), "обычный", False
            )
        permissions = guild.create_text_channel.call_args.kwargs["overwrites"]
        self.assertEqual(permissions[restricted_role], restriction)
        category.edit.assert_not_awaited()

    async def test_created_role_remains_tracked_if_later_creation_fails(self):
        role = MagicMock(spec=discord.Role)
        role.id = 200
        guild = MagicMock(
            spec=discord.Guild,
            id=10,
            roles=[],
            categories=[],
            create_role=AsyncMock(return_value=role),
            create_category=AsyncMock(
                side_effect=discord.Forbidden(
                    MagicMock(
                        spec=aiohttp.ClientResponse, status=403, reason="Forbidden"
                    ),
                    "Нет прав",
                )
            ),
        )
        with (
            patch("bot.cogs.builder.ROLES_CONFIG", [RoleConfig("роль", 0)]),
            patch("bot.cogs.builder.SERVER_STRUCTURE", [CategoryConfig(name="новая")]),
            self.assertRaises(discord.Forbidden),
        ):
            await self.builder._build(
                interaction(guild, channel(1, "команды")), "обычный", False
            )
        self.assertEqual(await self.store.ids(guild.id), {role.id})

    async def test_empty_owned_category_can_be_deleted(self):
        current = channel(1, "команды")
        category = channel(2, "пустая", kind=discord.CategoryChannel)
        category.channels = []
        guild = MagicMock(
            spec=discord.Guild, id=10, channels=[current, category], roles=[], me=None
        )
        await self.store.add(guild.id, category.id)
        await reset(self.builder, interaction(guild, current), confirm=True)
        category.delete.assert_awaited_once()
        self.assertEqual(await self.store.ids(guild.id), set())

    async def test_build_and_reset_cannot_run_concurrently(self):
        guild = MagicMock(spec=discord.Guild, id=10)
        request = interaction(guild, channel(1, "команды"))
        lock = asyncio.Lock()
        self.builder._locks[guild.id] = lock
        async with lock:
            with patch.object(self.builder, "_build", AsyncMock()) as build:
                callback = cast(
                    Callable[
                        [
                            Builder,
                            discord.Interaction,
                            bool,
                            discord.app_commands.Choice[str] | None,
                        ],
                        Awaitable[None],
                    ],
                    self.builder.build.callback,
                )
                await callback(self.builder, request, False, None)
                await reset(self.builder, request, confirm=True)
        build.assert_not_awaited()
        self.assertEqual(request.followup.send.await_count, 2)
