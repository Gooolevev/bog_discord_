"""Автопостройка современной структуры сервера с нативными фичами Discord."""

import asyncio
import logging
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.resources import ResourceStore

log = logging.getLogger(__name__)

# --- Структуры данных для продвинутой конфигурации ---


@dataclass(frozen=True)
class RoleConfig:
    name: str
    color: int
    hoist: bool = True
    mentionable: bool = False
    permissions: discord.Permissions = field(default_factory=discord.Permissions.none)


@dataclass(frozen=True)
class ForumTagConfig:
    name: str
    emoji: str
    moderated: bool = False  # Если True, ставить тег могут только модераторы


@dataclass(frozen=True)
class TextChannelConfig:
    name: str
    topic: str = ""
    slowmode: int = 0
    is_news: bool = False  # Делает канал новостным (с кнопкой "Подписаться"), если включено Сообщество
    pin_first_message: bool = False
    first_message_title: str = ""
    first_message: str = ""


@dataclass(frozen=True)
class ForumChannelConfig:
    name: str
    topic: str  # В форумах topic — это "Правила публикации" (Guidelines)
    tags: list[ForumTagConfig] = field(default_factory=list)
    default_reaction: str = "❤️"
    is_gallery: bool = False  # True = вид карточками (для скринов), False = списком


@dataclass(frozen=True)
class VoiceChannelConfig:
    name: str
    user_limit: int = 0
    bitrate: int = 64000  # В битах (64000 = 64 kbps, 96000 = 96 kbps для музыки)
    is_afk: bool = False
    is_stage: bool = (
        False  # True = создаст Трибуну (StageChannel) вместо обычного войса
    )


@dataclass(frozen=True)
class CategoryConfig:
    name: str
    text_channels: list[TextChannelConfig] = field(default_factory=list)
    forum_channels: list[ForumChannelConfig] = field(default_factory=list)
    voice_channels: list[VoiceChannelConfig] = field(default_factory=list)
    access_mode: str = "public"  # "public" | "read_only" | "staff_only"


# Discord тормозит массовое создание/удаление каналов — держим темп,
# чтобы не словить 429 и не получить «полу-созданный» сервер
CREATE_PAUSE = 0.6
DELETE_PAUSE = 0.4

# Discord не даёт менять шрифт напрямую, но пропускает юникод-двойников букв.
# Ключ — название стиля, значение — алфавит (только строчные: Discord режет заглавные).
CHANNEL_FONTS = {
    "обычный": None,
    "нежный курсив": "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧",
    "воздушный": "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏",
    "sans-serif жирный курсив": "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯",
}
_ASCII_LOWER = "abcdefghijklmnopqrstuvwxyz"


def stylize(text: str, font: str) -> str:
    """Перевести название канала в выбранный юникод-стиль."""
    alphabet = CHANNEL_FONTS.get(font)
    if alphabet is None:
        return text
    return text.translate(str.maketrans(_ASCII_LOWER, alphabet))


# --- Ключевые имена ролей ---

MEMBER_ROLE_NAME = "🌱・Участник"
MOD_ROLE_NAME = "🔧・Модератор"
ADMIN_ROLE_NAME = "🛡️・Администратор"


# --- Конфигурация ролей с реальными правами Discord ---

ROLES_CONFIG = [
    RoleConfig(
        name=MEMBER_ROLE_NAME,
        color=0x95A5A6,
        hoist=False,
        permissions=discord.Permissions(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True,
            connect=True,
            speak=True,
            use_voice_activation=True,
            change_nickname=True,
        ),
    ),
    RoleConfig("✨・Актив", 0x2ECC71),
    RoleConfig("💎・Бустер", 0xE91E63),
    RoleConfig(
        name=MOD_ROLE_NAME,
        color=0x3498DB,
        mentionable=True,
        permissions=discord.Permissions(
            kick_members=True,
            ban_members=True,
            moderate_members=True,  # Тайм-ауты (мьюты)
            manage_messages=True,
            manage_threads=True,
            mute_members=True,
            move_members=True,
            view_audit_log=True,
        ),
    ),
    RoleConfig(
        name=ADMIN_ROLE_NAME,
        color=0xE67E22,
        permissions=discord.Permissions(administrator=True),
    ),
    RoleConfig(
        name="👑・Владелец",
        color=0xE74C3C,
        permissions=discord.Permissions(administrator=True),
    ),
]


# --- Продвинутая структура сервера ---

SERVER_STRUCTURE = [
    CategoryConfig(
        name="🏛️ ┆ INFO",
        access_mode="read_only",
        text_channels=[
            TextChannelConfig(
                name="👋・welcome",
                topic="Старт: навигация, правила и первые шаги ✨",
                pin_first_message=True,
                first_message_title="👋 Добро пожаловать!",
                first_message=(
                    "👋 **Добро пожаловать!**\n"
                    "> Рады видеть тебя в комьюнити. Вот короткий маршрут по серверу.\n\n"
                    "🧭 **Навигация**\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "📜 {rules} — прочитай первым делом\n"
                    "📢 {news} — новости, события и обновления\n"
                    "💬 {chat} — главный чат сервера\n"
                    "📸 {media} — галерея, билды и творчество\n"
                    "🤝 {lfg} — поиск тиммейтов и пати\n\n"
                    "✨ Когда будешь готов — залетай в {chat} и просто напиши «ку»."
                ),
            ),
            TextChannelConfig(
                name="📜・rules",
                topic="Законы сервера. Незнание не освобождает от ответственности.",
                pin_first_message=True,
                first_message_title="📜 Правила сообщества",
                first_message=(
                    "📜 **Правила сообщества**\n"
                    "> Адекватность — главная валюта сервера.\n\n"
                    "**1. Уважение**\n"
                    "Без оскорблений, травли, токсичности, провокаций и переходов на личности.\n\n"
                    "**2. Чистый чат**\n"
                    "Без спама, флуда, капса, рекламы и левых ссылок без разрешения.\n\n"
                    "**3. Безопасный контент**\n"
                    "Запрещены NSFW, шок-контент, политика и материалы 18+.\n\n"
                    "**4. Модерация**\n"
                    "Слово модератора — закон. Спорные ситуации решаются в ЛС или через тикет.\n\n"
                    "✅ Прочитал — значит можно спокойно общаться."
                ),
            ),
            TextChannelConfig(
                name="📢・news",
                topic="Главные апдейты, события и анонсы сервера",
                is_news=True,
                pin_first_message=True,
                first_message_title="📢 Канал новостей",
                first_message=(
                    "📢 **Канал новостей**\n"
                    "> Здесь только важное: апдейты, события и анонсы.\n\n"
                    "**Что тут будет:**\n"
                    "• 🚀 Обновления сервера\n"
                    "• 🎉 Ивенты и конкурсы\n"
                    "• 🎁 Розыгрыши и бонусы\n"
                    "• 📌 Важные изменения разделов и правил"
                ),
            ),
            TextChannelConfig(
                name="💎・boost",
                topic="Зал славы бустеров и плюшки за поддержку",
                first_message_title="💎 Поддержка сервера",
                first_message=(
                    "💎 **Зал славы бустеров**\n"
                    "> Огромное спасибо каждому, кто поддерживает сервер! 💜\n\n"
                    "**Бонусы для бустеров:**\n"
                    "• 💎 Роль и выделение в списке участников\n"
                    "• 🎙️ Приоритет в голосовых каналах\n"
                    "• 🖼️ Возможность предложить эмодзи/стикер\n"
                    "• ✨ Отдельное уважение в комьюнити"
                ),
            ),
        ],
    ),
    CategoryConfig(
        name="💬 ┆ SOCIAL",
        access_mode="public",
        text_channels=[
            TextChannelConfig(
                name="💭・chat",
                topic="Главный чат: общение, мемы, игры и всё подряд",
                slowmode=2,
                first_message_title="💬 Главный чат открыт",
                first_message=(
                    "💬 **Главный чат**\n"
                    "> Общайся, делись мемами и будь на вайбе.\n\n"
                    "**Коротко:**\n"
                    "• Без токсичности\n"
                    "• Без спама и рекламы\n"
                    "• Уважай других участников"
                ),
            ),
            TextChannelConfig(
                name="🤖・bots",
                topic="Команды ботов, мини-игры и тесты",
                first_message_title="🤖 Терминал ботов",
                first_message=(
                    "🤖 **Терминал ботов**\n"
                    "> Здесь можно вызывать ботов, тестить команды и играть в мини-игры."
                ),
            ),
        ],
        forum_channels=[
            ForumChannelConfig(
                name="📸・media",
                topic="Галерея: скрины, билды, арты, мемы и ИРЛ. Один пост — одна тема.",
                default_reaction="🔥",
                is_gallery=True,
                tags=[
                    ForumTagConfig("Скриншот", "🖼️"),
                    ForumTagConfig("Постройка", "🏰"),
                    ForumTagConfig("Арт", "🎨"),
                    ForumTagConfig("ИРЛ", "🐾"),
                ],
            ),
        ],
    ),
    CategoryConfig(
        name="🎮 ┆ GAMING",
        access_mode="public",
        text_channels=[
            TextChannelConfig(
                name="⛏️・minecraft",
                topic="Выживание, моды, фермы, базы и совместные проекты",
                pin_first_message=True,
                first_message_title="⛏️ Уголок крафтеров",
                first_message=(
                    "⛏️ **Minecraft-хаб**\n"
                    "> Обсуждаем ваниллу, сборки, фермы, постройки и координаты.\n"
                    "Делись прогрессом и ищи помощников для мегабилдов."
                ),
            ),
            TextChannelConfig(
                name="🏆・events",
                topic="Турниры, конкурсы, розыгрыши и совместные события",
                first_message_title="🏆 Ивент-зона",
                first_message=(
                    "🏆 **Ивент-зона**\n"
                    "> Здесь будут турниры, конкурсы, розыгрыши и движ-события."
                ),
            ),
        ],
        forum_channels=[
            ForumChannelConfig(
                name="🤝・lfg",
                topic="Ищешь пати, напарника или совет по игре? Создай пост и выбери теги.",
                default_reaction="🎮",
                is_gallery=False,
                tags=[
                    ForumTagConfig("Ищу пати", "🤝"),
                    ForumTagConfig("Майнкрафт", "⛏️"),
                    ForumTagConfig("Шутеры", "🔫"),
                    ForumTagConfig("Гайд / вопрос", "❓"),
                ],
            ),
        ],
    ),
    CategoryConfig(
        name="🎧 ┆ VOICE",
        access_mode="public",
        voice_channels=[
            VoiceChannelConfig("🎙️・stage", is_stage=True),
            VoiceChannelConfig("☕・lounge"),
            VoiceChannelConfig("🎶・music", bitrate=96000),
            VoiceChannelConfig("🎮・duo", user_limit=2),
            VoiceChannelConfig("⚔️・squad-1", user_limit=5),
            VoiceChannelConfig("⚔️・squad-2", user_limit=5),
            VoiceChannelConfig("💤・afk", is_afk=True),
        ],
    ),
    CategoryConfig(
        name="🛡️ ┆ STAFF",
        access_mode="staff_only",
        text_channels=[
            TextChannelConfig(
                name="🛡️・staff-chat",
                topic="Закрытый чат администрации и модераторов",
                pin_first_message=True,
                first_message_title="🛡️ Штаб управления",
                first_message=(
                    "🛡️ **Штаб управления**\n"
                    "> Раздел доступен только модераторам и администрации."
                ),
            ),
            TextChannelConfig(
                name="📋・logs",
                topic="Системные отчёты, журнал действий и вебхуки",
                first_message_title="📋 Канал логирования",
                first_message=(
                    "📋 **Логи**\n"
                    "> Сюда можно привязать вебхуки, логи модерации и системные события."
                ),
            ),
        ],
        voice_channels=[
            VoiceChannelConfig("🔑・meeting", user_limit=10),
        ],
    ),
]


# --- Ког ---


class Builder(commands.Cog):
    """Создаёт структуру сервера и хранит ID принадлежащих боту объектов."""

    def __init__(self, bot: commands.Bot, store: ResourceStore | None = None) -> None:
        self.bot = bot
        self.store = store or ResourceStore()
        self._locks: dict[int, asyncio.Lock] = {}

    async def cog_load(self) -> None:
        await self.store.initialize()

    async def _remember(self, guild_id: int, resource: discord.abc.Snowflake) -> None:
        await self.store.add(guild_id, resource.id)
        await asyncio.sleep(CREATE_PAUSE)

    def _overwrites(
        self, guild: discord.Guild, roles: dict[str, discord.Role], mode: str
    ) -> dict:
        overwrites = {}
        if mode == "read_only":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
                connect=False,
            )
            if role := roles.get(MOD_ROLE_NAME):
                overwrites[role] = discord.PermissionOverwrite(
                    send_messages=True,
                    add_reactions=True,
                    manage_messages=True,
                )
        elif mode == "staff_only":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=False
            )
            for name in (MOD_ROLE_NAME, ADMIN_ROLE_NAME):
                if role := roles.get(name):
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        connect=True,
                        speak=True,
                    )
        if mode != "public" and guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            )
        return overwrites

    @app_commands.command(
        name="построй", description="Создать роли и структуру сервера"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        clean="Удалить созданные ботом текстовые каналы, оставшиеся без категории",
        шрифт="Стиль названий каналов",
    )
    @app_commands.choices(
        шрифт=[
            app_commands.Choice(name=name.capitalize(), value=name)
            for name in CHANNEL_FONTS
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(administrator=True)
    async def build(
        self,
        interaction: discord.Interaction,
        clean: bool = False,
        шрифт: app_commands.Choice[str] | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда работает только на сервере.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        lock = self._locks.setdefault(interaction.guild.id, asyncio.Lock())
        if lock.locked():
            await interaction.followup.send(
                "⏳ На сервере уже идёт постройка или сброс.", ephemeral=True
            )
            return
        async with lock:
            await self._build(interaction, шрифт.value if шрифт else "обычный", clean)

    async def _build(
        self, interaction: discord.Interaction, style: str, clean: bool
    ) -> None:
        guild = interaction.guild
        assert guild is not None
        owned = await self.store.ids(guild.id)
        created = {
            "🎭 Роли": 0,
            "📁 Категории": 0,
            "💬 Текстовые": 0,
            "🗂️ Форумы": 0,
            "🔊 Голосовые / Сцены": 0,
        }
        roles = {role.name: role for role in guild.roles}
        channels: dict[str, discord.abc.GuildChannel] = {}
        welcome: tuple[discord.TextChannel, TextChannelConfig] | None = None
        afk_channel = None

        for cfg in ROLES_CONFIG:
            if cfg.name not in roles:
                role = await guild.create_role(
                    name=cfg.name,
                    color=discord.Color(cfg.color),
                    hoist=cfg.hoist,
                    mentionable=cfg.mentionable,
                    permissions=cfg.permissions,
                    reason="Автопостройка сервера",
                )
                await self._remember(guild.id, role)
                roles[cfg.name] = role
                created["🎭 Роли"] += 1

        for cfg in SERVER_STRUCTURE:
            name = stylize(cfg.name, style)
            overwrites = self._overwrites(guild, roles, cfg.access_mode)
            category = discord.utils.get(guild.categories, name=name)
            if category is None:
                category = await guild.create_category(
                    name=name, overwrites=overwrites, reason="Автопостройка сервера"
                )
                await self._remember(guild.id, category)
                created["📁 Категории"] += 1
            elif overwrites and category.id in owned:
                await category.edit(
                    overwrites=category.overwrites | overwrites,
                    reason="Обновление прав категории",
                )
            # У существующей категории могут быть дополнительные ограничения доступа.
            channel_overwrites = category.overwrites | overwrites

            for text in cfg.text_channels:
                channel = discord.utils.get(
                    category.text_channels, name=stylize(text.name, style)
                )
                if channel is None:
                    channel = await guild.create_text_channel(
                        name=stylize(text.name, style),
                        category=category,
                        topic=text.topic,
                        slowmode_delay=text.slowmode,
                        news=text.is_news and "COMMUNITY" in guild.features,
                        overwrites=channel_overwrites,
                        reason="Автопостройка сервера",
                    )
                    await self._remember(guild.id, channel)
                    owned.add(channel.id)
                    created["💬 Текстовые"] += 1
                    if text.first_message and "welcome" not in text.name:
                        await self._send_starter_embed(channel, text)
                channels[text.name] = channel
                if "welcome" in text.name and channel.id in owned:
                    welcome = channel, text

            for forum in cfg.forum_channels:
                name = stylize(forum.name, style)
                channel = discord.utils.get(
                    category.forums, name=name
                ) or discord.utils.get(category.text_channels, name=name)
                if channel is None:
                    if "COMMUNITY" in guild.features:
                        channel = await guild.create_forum(
                            name=name,
                            topic=forum.topic,
                            category=category,
                            overwrites=channel_overwrites,
                            default_layout=discord.ForumLayoutType.gallery_view
                            if forum.is_gallery
                            else discord.ForumLayoutType.list_view,
                            default_reaction_emoji=forum.default_reaction,
                            available_tags=[
                                discord.ForumTag(
                                    name=t.name, emoji=t.emoji, moderated=t.moderated
                                )
                                for t in forum.tags
                            ],
                            reason="Автопостройка сервера",
                        )
                        created["🗂️ Форумы"] += 1
                    else:
                        channel = await guild.create_text_channel(
                            name=name,
                            category=category,
                            topic=forum.topic,
                            overwrites=channel_overwrites,
                            reason="Текстовый аналог форума",
                        )
                        created["💬 Текстовые"] += 1
                    await self._remember(guild.id, channel)
                channels[forum.name] = channel

            for voice in cfg.voice_channels:
                name = stylize(voice.name, style)
                channel = discord.utils.get(
                    category.stage_channels, name=name
                ) or discord.utils.get(category.voice_channels, name=name)
                if channel is None:
                    if voice.is_stage and "COMMUNITY" in guild.features:
                        channel = await guild.create_stage_channel(
                            name=name,
                            category=category,
                            overwrites=channel_overwrites,
                            reason="Автопостройка сервера",
                        )
                    else:
                        channel = await guild.create_voice_channel(
                            name=name,
                            category=category,
                            user_limit=voice.user_limit,
                            bitrate=min(voice.bitrate, int(guild.bitrate_limit)),
                            overwrites=channel_overwrites,
                            reason="Автопостройка сервера",
                        )
                    await self._remember(guild.id, channel)
                    created["🔊 Голосовые / Сцены"] += 1
                if voice.is_afk and isinstance(channel, discord.VoiceChannel):
                    afk_channel = channel

        if welcome:
            channel, cfg = welcome
            links = {
                key: channels[name].mention if name in channels else f"**#{name}**"
                for key, name in {
                    "rules": "📜・rules",
                    "news": "📢・news",
                    "chat": "💭・chat",
                    "media": "📸・media",
                    "lfg": "🤝・lfg",
                }.items()
            }
            await self._send_starter_embed(
                channel, cfg, cfg.first_message.format(**links), refresh=True
            )

        settings = {}
        if afk_channel is not None:
            settings.update(afk_channel=afk_channel, afk_timeout=900)
        if "👋・welcome" in channels:
            settings.update(
                system_channel=channels["👋・welcome"],
                system_channel_flags=discord.SystemChannelFlags(
                    join_notifications=True,
                    premium_subscriptions=True,
                ),
            )
        warnings = 0
        if settings:
            try:
                await guild.edit(**settings, reason="Настройка системных каналов")
            except discord.HTTPException as error:
                log.warning(
                    "Системные каналы сервера %s: HTTP %s", guild.id, error.status
                )
                warnings += 1

        deleted = 0
        if clean:
            for channel in guild.text_channels:
                if (
                    channel.id in owned
                    and channel.category_id is None
                    and channel.id != interaction.channel_id
                ):
                    if await self._delete(guild.id, channel):
                        deleted += 1
                    else:
                        warnings += 1
        embed = discord.Embed(
            title="🏗️ Постройка завершена", color=discord.Color.blurple()
        )
        for name, count in created.items():
            embed.add_field(name=name, value=f"+{count}")
        embed.add_field(name="🧹 Очистка", value=f"−{deleted}")
        if warnings:
            embed.description = (
                f"⚠️ Не удалось выполнить операций: {warnings}. Подробности в журнале."
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _send_starter_embed(
        self,
        channel: discord.TextChannel,
        cfg: TextChannelConfig,
        description: str | None = None,
        *,
        refresh: bool = False,
    ) -> None:
        embed = discord.Embed(
            title=cfg.first_message_title or f"#{channel.name}",
            description=description or cfg.first_message,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=channel.guild.name)
        if refresh:
            async for message in channel.history(limit=20):
                if (
                    message.author == self.bot.user
                    and message.embeds
                    and message.embeds[0].title == embed.title
                ):
                    await message.edit(embed=embed)
                    return
        message = await channel.send(embed=embed)
        if cfg.pin_first_message:
            try:
                await message.pin(reason="Стартовое сообщение")
            except discord.HTTPException as error:
                log.warning(
                    "Закрепление в канале %s: HTTP %s", channel.id, error.status
                )

    async def _delete(
        self, guild_id: int, resource: discord.abc.GuildChannel | discord.Role
    ) -> bool:
        try:
            await resource.delete(reason="Удаление объекта, созданного ботом")
        except discord.NotFound:
            # Объект уже удалён вручную; запись больше не нужна.
            await self.store.remove(guild_id, resource.id)
            return True
        except discord.HTTPException as error:
            log.warning(
                "Удаление объекта %s на сервере %s: HTTP %s",
                resource.id,
                guild_id,
                error.status,
            )
            return False
        await self.store.remove(guild_id, resource.id)
        await asyncio.sleep(DELETE_PAUSE)
        return True

    @app_commands.command(
        name="ресет", description="Удалить только объекты, созданные и учтённые ботом"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        каналы="Удалить созданные ботом каналы и пустые категории, кроме текущих",
        роли="Удалить созданные ботом роли",
        подтвердить="Подтвердить удаление; без этого параметра будет только предварительный просмотр",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def reset(
        self,
        interaction: discord.Interaction,
        каналы: bool = True,
        роли: bool = True,
        подтвердить: bool = False,
    ) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Вызывай команду из текстового канала сервера.", ephemeral=True
            )
            return
        if not каналы and not роли:
            await interaction.response.send_message(
                "❌ Оба параметра выключены.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        lock = self._locks.setdefault(guild.id, asyncio.Lock())
        if lock.locked():
            await interaction.followup.send(
                "⏳ На сервере уже идёт постройка или сброс.", ephemeral=True
            )
            return
        async with lock:
            owned = await self.store.ids(guild.id)
            targets = [
                ch
                for ch in guild.channels
                if каналы
                and ch.id in owned
                and ch.id
                not in (
                    interaction.channel_id,
                    interaction.channel.category_id,
                )
            ]
            role_targets = [
                role
                for role in guild.roles
                if роли
                and role.id in owned
                and not role.is_default()
                and not role.managed
                and guild.me is not None
                and role < guild.me.top_role
            ]
            if not подтвердить:
                await interaction.followup.send(
                    f"Будут удалены объекты бота: каналов/категорий — {len(targets)}, ролей — {len(role_targets)}.\n"
                    "Категории с оставшимися каналами сохранятся. Удаление каналов и сообщений необратимо.\n"
                    "Для выполнения повтори `/ресет` с теми же параметрами и `подтвердить: True`.\n"
                    "Старые объекты без записи о создании ботом не удаляются.",
                    ephemeral=True,
                )
                return
            deleted: set[int] = set()
            failed = 0
            categories = [
                ch for ch in targets if isinstance(ch, discord.CategoryChannel)
            ]
            resources = [
                ch for ch in targets if not isinstance(ch, discord.CategoryChannel)
            ]
            for resource in [*resources, *role_targets]:
                if await self._delete(guild.id, resource):
                    deleted.add(resource.id)
                else:
                    failed += 1
            preserved = 0
            for category in categories:
                if any(ch.id not in deleted for ch in category.channels):
                    preserved += 1
                    continue
                if await self._delete(guild.id, category):
                    deleted.add(category.id)
                else:
                    failed += 1
            await interaction.followup.send(
                f"🧹 Удалено объектов бота: {len(deleted)}. Ошибок: {failed}. "
                f"Сохранено непустых категорий: {preserved}.",
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
        if role is not None and role not in member.roles:
            try:
                await member.add_roles(role, reason="Авто-роль новичка")
            except discord.HTTPException as error:
                log.warning(
                    "Авто-роль на сервере %s: HTTP %s", member.guild.id, error.status
                )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Builder(bot))
