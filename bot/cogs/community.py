"""Долговечные интерактивные опросы и сбор участников."""

import asyncio
import logging
import time
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.utils.community import Board, BoardError, CommunityStore, poll_options
from bot.utils.settings import SettingsStore
from bot.utils.ui import (
    MUTED,
    SUCCESS,
    WARNING,
    PersonalView,
    SafeModal,
    SafeView,
    card,
    plain,
    private,
)

log = logging.getLogger(__name__)


def board_embed(board: Board) -> discord.Embed:
    finished = board.closed or time.time() >= board.ends_at
    date = discord.utils.format_dt(datetime.fromtimestamp(board.ends_at, UTC), "R")
    if board.kind == "poll":
        title = "ОПРОС · Итоги" if finished else "ОПРОС · Решаем вместе"
    else:
        title = (
            "СБОР · Завершён"
            if finished
            else "СБОР · Команда собрана"
            if len(board.votes) >= board.capacity
            else "СБОР · Есть дело"
        )
    embed = card(
        title,
        plain(board.title, 4092),
        color=MUTED if finished else SUCCESS if board.kind == "party" else WARNING,
    )
    if board.kind == "poll":
        total = len(board.votes)
        counts = [
            sum(choice == i for choice in board.votes.values())
            for i in range(len(board.options))
        ]
        for index, (option, count) in enumerate(
            zip(board.options, counts, strict=True)
        ):
            percent = round(count / total * 100) if total else 0
            filled = round(count / total * 10) if total else 0
            embed.add_field(
                name=f"{index + 1}. {plain(option, 160)}",
                value=f"{'▰' * filled}{'▱' * (10 - filled)} **{percent}%** · {count}",
                inline=False,
            )
        if finished:
            best = max(counts, default=0)
            leaders = [
                plain(board.options[i], 160)
                for i, count in enumerate(counts)
                if count == best
            ]
            result = (
                "Нет голосов"
                if not total
                else ("Ничья: " if len(leaders) > 1 else "Выбрано: ")
                + " / ".join(leaders)
            )
            embed.add_field(name="Результат", value=result[:1024], inline=False)
        embed.add_field(
            name="Участие",
            value=f"**{total}** голосов · один ответ на участника",
            inline=False,
        )
        if not finished:
            embed.add_field(
                name="Как участвовать",
                value="Нажми «Голосовать». Ответ можно изменить или снять.\nВыбор сохраняется без публикации имени голосующего.",
                inline=False,
            )
    else:
        names = [f"<@{user_id}>" for user_id in board.votes]
        for offset in range(0, max(1, len(names)), 20):
            embed.add_field(
                name=f"Команда · {len(board.votes)}/{board.capacity}"
                if offset == 0
                else "Продолжение команды",
                value=" · ".join(names[offset : offset + 20])
                or "Пока никто не записался",
                inline=False,
            )
        if not finished:
            embed.add_field(
                name="Дальше",
                value="Запишись кнопкой ниже.\nКогда место освобождается, его может занять другой участник.",
                inline=False,
            )
    embed.add_field(
        name="Статус",
        value="Завершено"
        if finished
        else f"{'Начало' if board.kind == 'party' else 'Итоги'} {date}",
        inline=True,
    )
    embed.add_field(name="Организатор", value=f"<@{board.author_id}>", inline=True)
    embed.set_footer(
        text="СООБЩЕСТВО • карточка и ответы сохраняются после перезапуска"
    )
    # Экранирование текста увеличивает длину; длинный вопрос и ничья по всем
    # вариантам вместе тоже должны укладываться в общий лимит Embed.
    if len(embed) > 5900:
        available = 5900 - len(embed) + len(embed.description)
        embed.description = embed.description[: available - 1] + "…"
    return embed


class VoteSelect(discord.ui.Select):
    def __init__(self, board: Board, user_id: int):
        super().__init__(
            placeholder="Выбери один вариант",
            options=[
                discord.SelectOption(
                    label=option, value=str(i), default=board.votes.get(user_id) == i
                )
                for i, option in enumerate(board.options)
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.submit(interaction, int(self.values[0]))


class VoteView(PersonalView):
    def __init__(self, cog: "Community", board: Board, user_id: int):
        super().__init__(user_id, timeout=120)
        self.cog = cog
        self.board = board
        self.add_item(VoteSelect(board, user_id))

    async def submit(self, interaction: discord.Interaction, choice: int) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            async with self.cog.lock_for(self.board.message_id):
                board = await self.cog.store.act(
                    self.board.id, interaction.guild_id, interaction.user.id, choice
                )
                await self.cog.render(board)
        except BoardError as error:
            await private(interaction, str(error))
            return
        await interaction.edit_original_response(
            content="Голос сохранён. Общая карточка обновлена.", view=None
        )
        self.stop()


class PollView(SafeView):
    def __init__(self, cog: "Community"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Голосовать",
        emoji="🗳️",
        style=discord.ButtonStyle.primary,
        custom_id="community:poll:vote",
    )
    async def vote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            board = await self.cog.lookup(interaction)
            if board.closed or time.time() >= board.ends_at:
                raise BoardError(
                    "Опрос уже завершён. Обнови карточку, чтобы увидеть итоги."
                )
        except BoardError as error:
            await private(interaction, str(error))
            return
        view = VoteView(self.cog, board, interaction.user.id)
        self.cog._vote_views = {
            item for item in self.cog._vote_views if not item.is_finished()
        }
        self.cog._vote_views.add(view)
        view.message = await interaction.followup.send(
            "Выбери ответ. В общей карточке видны только суммы голосов.",
            view=view,
            ephemeral=True,
            wait=True,
        )

    @discord.ui.button(
        label="Снять голос",
        style=discord.ButtonStyle.secondary,
        custom_id="community:poll:withdraw",
    )
    async def withdraw(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction, -1)

    @discord.ui.button(
        label="Обновить",
        style=discord.ButtonStyle.secondary,
        custom_id="community:poll:refresh",
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction)

    @discord.ui.button(
        label="Завершить",
        style=discord.ButtonStyle.secondary,
        custom_id="community:poll:close",
    )
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction, close=True)


class PartyView(SafeView):
    def __init__(self, cog: "Community"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Я участвую",
        emoji="🙌",
        style=discord.ButtonStyle.success,
        custom_id="community:party:join",
    )
    async def join(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction, 0)

    @discord.ui.button(
        label="Выйти",
        style=discord.ButtonStyle.secondary,
        custom_id="community:party:leave",
    )
    async def leave(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction, -1)

    @discord.ui.button(
        label="Обновить",
        style=discord.ButtonStyle.secondary,
        custom_id="community:party:refresh",
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction)

    @discord.ui.button(
        label="Завершить сбор",
        style=discord.ButtonStyle.secondary,
        custom_id="community:party:close",
    )
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.cog.action(interaction, close=True)


class PublishModal(SafeModal):
    def __init__(self, cog: "Community", kind: str, default_minutes: int = 60):
        super().__init__(
            title="Опубликовать опрос" if kind == "poll" else "Опубликовать сбор",
            timeout=300,
        )
        self.cog = cog
        self.kind = kind
        self.topic = discord.ui.TextInput(
            label="Тема",
            max_length=1000 if kind == "poll" else 180,
            style=discord.TextStyle.paragraph,
        )
        self.details = discord.ui.TextInput(
            label="Варианты через ;" if kind == "poll" else "Всего мест, включая тебя",
            placeholder="Строим порт; Идём в шахту; Исследуем мир"
            if kind == "poll"
            else "5",
            default=None if kind == "poll" else "5",
            required=kind != "poll",
            max_length=500 if kind == "poll" else 2,
        )
        self.minutes = discord.ui.TextInput(
            label="Через сколько минут подвести итог / начать?",
            default=str(default_minutes),
            max_length=4,
        )
        for item in (self.topic, self.details, self.minutes):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            minutes = int(str(self.minutes))
            capacity = int(str(self.details)) if self.kind == "party" else 0
        except ValueError:
            await private(
                interaction, "Время и число мест нужно указать целыми числами."
            )
            return
        await self.cog.publish(
            interaction,
            self.kind,
            str(self.topic),
            str(self.details) if self.kind == "poll" else None,
            capacity,
            minutes,
        )


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store = CommunityStore()
        self.poll_view = PollView(self)
        self.party_view = PartyView(self)
        self._locks = [asyncio.Lock() for _ in range(32)]
        self._refresh_after: dict[int, float] = {}
        self._vote_views: set[VoteView] = set()

    async def poll_minutes(self, guild_id: int) -> int:
        settings = getattr(self.bot, "settings", None)
        if isinstance(settings, SettingsStore):
            return (await settings.get(guild_id))["poll_minutes"]
        return 60

    def lock_for(self, message_id: int) -> asyncio.Lock:
        return self._locks[message_id % len(self._locks)]

    async def cog_load(self) -> None:
        await self.store.initialize()
        self.bot.add_view(self.poll_view)
        self.bot.add_view(self.party_view)
        self.expire.start()

    async def cog_unload(self) -> None:
        self.expire.cancel()
        task = self.expire.get_task()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        self.poll_view.stop()
        self.party_view.stop()
        for view in self._vote_views:
            view.stop()
        self._vote_views.clear()

    async def lookup(self, interaction: discord.Interaction) -> Board:
        if interaction.guild_id is None or interaction.message is None:
            raise BoardError("Карточки работают только в каналах сервера.")
        return await self.store.for_message(
            interaction.guild_id, interaction.message.id
        )

    async def render(self, board: Board) -> None:
        finished = board.closed or time.time() >= board.ends_at
        message = self.bot.get_partial_messageable(
            board.channel_id
        ).get_partial_message(board.message_id)
        await message.edit(
            embed=board_embed(board),
            view=None
            if finished
            else self.poll_view
            if board.kind == "poll"
            else self.party_view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if finished:
            await self.store.published(board)

    async def action(
        self,
        interaction: discord.Interaction,
        choice: int | None = None,
        *,
        close: bool = False,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            board = await self.lookup(interaction)
            async with self.lock_for(board.message_id):
                if choice is not None or close:
                    board = await self.store.act(
                        board.id,
                        interaction.guild_id,
                        interaction.user.id,
                        choice if choice is not None else -1,
                        close=close,
                        moderator=interaction.permissions.manage_messages,
                    )
                else:
                    now = time.monotonic()
                    if self._refresh_after.get(board.message_id, 0) > now:
                        raise BoardError(
                            "Карточка только что обновлена. Подожди 5 секунд."
                        )
                    self._refresh_after = {
                        key: value
                        for key, value in self._refresh_after.items()
                        if value > now
                    }
                    self._refresh_after[board.message_id] = now + 5
                    board = await self.store.get(board.id, interaction.guild_id)
                await self.render(board)
        except BoardError as error:
            await private(interaction, str(error))
            return
        await private(
            interaction,
            "Карточка обновлена." if choice is None else "Готово, изменение сохранено.",
        )

    async def publish(
        self,
        interaction: discord.Interaction,
        kind: str,
        title: str,
        options: str | None = None,
        capacity: int = 5,
        minutes: int | None = None,
    ) -> None:
        if interaction.guild_id is None or interaction.channel_id is None:
            await private(interaction, "Опросы и сборы доступны только на сервере.")
            return
        in_thread = isinstance(interaction.channel, discord.Thread)
        user_can_send = (
            interaction.permissions.send_messages_in_threads
            if in_thread
            else interaction.permissions.send_messages
        )
        bot_can_send = (
            interaction.app_permissions.send_messages_in_threads
            if in_thread
            else interaction.app_permissions.send_messages
        )
        if not user_can_send:
            await private(
                interaction,
                "Для публикации нужно право отправлять сообщения в этом канале.",
            )
            return
        if not bot_can_send or not interaction.app_permissions.embed_links:
            await private(
                interaction,
                "Боту нужны права отправки сообщений и встраивания ссылок в этом канале.",
            )
            return
        await interaction.response.defer(ephemeral=True)
        try:
            if minutes is None:
                minutes = (
                    await self.poll_minutes(interaction.guild_id)
                    if kind == "poll"
                    else 60
                )
            board = await self.store.create(
                interaction.guild_id,
                interaction.channel_id,
                interaction.user.id,
                kind,
                title,
                poll_options(options) if kind == "poll" else [],
                capacity,
                minutes,
            )
        except BoardError as error:
            await private(interaction, str(error))
            return
        try:
            # Обычное сообщение бота доступно для обновления и после истечения webhook-токена.
            channel = self.bot.get_partial_messageable(board.channel_id)
            message = await channel.send(
                embed=board_embed(board),
                view=self.poll_view if kind == "poll" else self.party_view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            try:
                await self.store.attach(board, message.id)
            except Exception:
                await message.edit(
                    content="Не удалось сохранить карточку. Создай её заново.",
                    embed=None,
                    view=None,
                )
                raise
        except Exception:
            await self.store.discard(board)
            raise
        await private(interaction, f"Готово: [открыть карточку]({message.jump_url}).")

    @app_commands.command(
        name="сбор", description="Собрать команду: запись, лимит мест и время начала"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(
        тема="Что будем делать?",
        мест="Всего мест, включая организатора",
        через="Начало через указанное число минут",
    )
    async def party(
        self,
        interaction: discord.Interaction,
        тема: app_commands.Range[str, 1, 180],
        мест: app_commands.Range[int, 2, 50] = 5,
        через: app_commands.Range[int, 1, 1440] = 60,
    ) -> None:
        await self.publish(interaction, "party", тема, capacity=мест, minutes=через)

    @tasks.loop(seconds=30)
    async def expire(self) -> None:
        try:
            for board in await self.store.due():
                async with self.lock_for(board.message_id):
                    try:
                        await self.render(
                            await self.store.get(board.id, board.guild_id)
                        )
                    except discord.NotFound:
                        await self.store.published(board)
                    except discord.HTTPException as error:
                        log.warning(
                            "Завершение карточки %s: HTTP %s", board.id, error.status
                        )
        except Exception as error:  # noqa: BLE001 — следующий цикл должен повторить обновление
            log.error("Обновление карточек: %s", type(error).__name__)

    @expire.before_loop
    async def before_expire(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Community(bot))
