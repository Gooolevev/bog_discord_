"""Автопостройка современной структуры сервера с нативными фичами Discord."""

import asyncio
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

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
    is_stage: bool = False  # True = создаст Трибуну (StageChannel) вместо обычного войса


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
    """Продвинутая постройка сервера с использованием Форумов, Трибуны и прав ролей."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="построй",
        description="Создать современную структуру сервера (форумы, трибуна, стафф-зона, роли)",
    )
    @app_commands.describe(
        clean="Удалить старые текстовые каналы без категорий",
        шрифт="Стиль названий каналов (обычный, нежный курсив, воздушный, sans-serif жирный курсив)",
    )
    @app_commands.choices(шрифт=[
        app_commands.Choice(name="Обычный", value="обычный"),
        app_commands.Choice(name="Нежный курсив", value="нежный курсив"),
        app_commands.Choice(name="Воздушный", value="воздушный"),
        app_commands.Choice(name="Sans-serif жирный курсив", value="sans-serif жирный курсив"),
    ])
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def build(
        self,
        interaction: discord.Interaction,
        clean: bool = False,
        шрифт: app_commands.Choice[str] | None = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Команда работает только на сервере.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        style = шрифт.value if шрифт is not None else "обычный"

        created_roles = 0
        created_categories = 0
        created_text = 0
        created_forums = 0
        created_voice = 0
        afk_channel = None

        # Словарь для хранения ссылок на ключевые каналы (чтобы сделать кликабельную навигацию)
        created_channels_map: dict[str, discord.abc.GuildChannel] = {}
        welcome_channel_And_cfg: tuple[discord.TextChannel, TextChannelConfig] | None = None

        # 1. Создаём роли с правами
        for role_cfg in ROLES_CONFIG:
            role = discord.utils.get(guild.roles, name=role_cfg.name)
            if role is None:
                await guild.create_role(
                    name=role_cfg.name,
                    color=discord.Color(role_cfg.color),
                    hoist=role_cfg.hoist,
                    mentionable=role_cfg.mentionable,
                    permissions=role_cfg.permissions,
                    reason="Автопостройка сервера",
                )
                created_roles += 1
                await asyncio.sleep(CREATE_PAUSE)

        mod_role = discord.utils.get(guild.roles, name=MOD_ROLE_NAME)
        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)

        # 2. Создаём категории и каналы
        for cat_cfg in SERVER_STRUCTURE:
            overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite] = {}

            if cat_cfg.access_mode == "read_only":
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    send_messages=False,
                    add_reactions=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    send_messages_in_threads=False,
                    connect=False,
                )
                if mod_role:
                    overwrites[mod_role] = discord.PermissionOverwrite(
                        send_messages=True,
                        add_reactions=True,
                        manage_messages=True,
                    )

            elif cat_cfg.access_mode == "staff_only":
                # Скрываем категорию от всех
                overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                # Открываем для модераторов, админов и самого бота
                if mod_role:
                    overwrites[mod_role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, connect=True, speak=True
                    )
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, connect=True, speak=True
                    )
                if guild.me:
                    overwrites[guild.me] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, manage_channels=True
                    )

            category = discord.utils.get(guild.categories, name=stylize(cat_cfg.name, style))
            if category is None:
                category = await guild.create_category(
                    name=stylize(cat_cfg.name, style),
                    overwrites=overwrites,
                    reason="Автопостройка сервера",
                )
                created_categories += 1
            elif overwrites:
                await category.edit(overwrites=overwrites, reason="Обновление прав категории")

            # 2.1 Текстовые каналы
            for text_cfg in cat_cfg.text_channels:
                existing_ch = discord.utils.get(category.text_channels, name=stylize(text_cfg.name, style))
                if existing_ch is not None:
                    created_channels_map[text_cfg.name] = existing_ch
                    continue

                # Проверяем, поддерживает ли сервер новостные каналы (нужна фича COMMUNITY)
                use_news = text_cfg.is_news and "COMMUNITY" in guild.features

                channel = await guild.create_text_channel(
                    name=stylize(text_cfg.name, style),
                    category=category,
                    topic=text_cfg.topic,
                    slowmode_delay=text_cfg.slowmode,
                    news=use_news,
                    reason="Автопостройка сервера",
                )
                created_text += 1
                created_channels_map[text_cfg.name] = channel
                await asyncio.sleep(CREATE_PAUSE)

                # Приветственный канал отложим на конец, чтобы подставить в него живые ссылки на остальные каналы
                if "welcome" in text_cfg.name:
                    welcome_channel_And_cfg = (channel, text_cfg)
                    continue

                if text_cfg.first_message:
                    await self._send_starter_embed(channel, text_cfg)

            # 2.2 Форумы (ForumChannel)
            for forum_cfg in cat_cfg.forum_channels:
                existing_forum = discord.utils.get(category.forums, name=stylize(forum_cfg.name, style))
                if existing_forum is not None:
                    created_channels_map[forum_cfg.name] = existing_forum
                    continue

                layout = (
                    discord.ForumLayoutType.gallery_view
                    if forum_cfg.is_gallery
                    else discord.ForumLayoutType.list_view
                )
                tags = [
                    discord.ForumTag(name=t.name, emoji=t.emoji, moderated=t.moderated)
                    for t in forum_cfg.tags
                ]

                try:
                    forum = await guild.create_forum(
                        name=stylize(forum_cfg.name, style),
                        topic=forum_cfg.topic,
                        category=category,
                        default_layout=layout,
                        default_reaction_emoji=forum_cfg.default_reaction,
                        available_tags=tags,
                        reason="Автопостройка сервера",
                    )
                    created_forums += 1
                    created_channels_map[forum_cfg.name] = forum
                    await asyncio.sleep(CREATE_PAUSE)
                except discord.HTTPException:
                    # Если на сервере запрещены форумы, создаём аккуратный текстовый аналог
                    fallback = await guild.create_text_channel(
                        name=stylize(forum_cfg.name, style),
                        category=category,
                        topic=forum_cfg.topic,
                        reason="Фолбэк форума при автопостройке",
                    )
                    created_text += 1
                    created_channels_map[forum_cfg.name] = fallback
                    await asyncio.sleep(CREATE_PAUSE)

            # 2.3 Голосовые каналы и Трибуны (StageChannel)
            for voice_cfg in cat_cfg.voice_channels:
                if voice_cfg.is_stage and discord.utils.get(category.stage_channels, name=stylize(voice_cfg.name, style)) is None:
                    try:
                            await guild.create_stage_channel(
                                name=stylize(voice_cfg.name, style),
                                category=category,
                                reason="Автопостройка сервера",
                            )
                            created_voice += 1
                            continue
                    except discord.HTTPException:
                        pass  # Если сервер без Сообщества, создастся как обычный войс ниже

                if discord.utils.get(category.voice_channels, name=stylize(voice_cfg.name, style)) is None:
                    # Ограничиваем битрейт лимитом сервера (на случай отсутствия бустов)
                    safe_bitrate = min(voice_cfg.bitrate, int(guild.bitrate_limit))
                    vc = await guild.create_voice_channel(
                        name=stylize(voice_cfg.name, style),
                        category=category,
                        user_limit=voice_cfg.user_limit,
                        bitrate=safe_bitrate,
                        reason="Автопостройка сервера",
                    )
                    created_voice += 1
                    await asyncio.sleep(CREATE_PAUSE)
                    if voice_cfg.is_afk:
                        afk_channel = vc

        # 3. Отправляем отложенное сообщение в канал приветствия с живыми упоминаниями (#канал)
        if welcome_channel_And_cfg is not None:
            w_channel, w_cfg = welcome_channel_And_cfg

            def mention_or_name(ch_name: str) -> str:
                ch = created_channels_map.get(ch_name)
                return ch.mention if ch else f"**#{ch_name}**"

            formatted_text = w_cfg.first_message.format(
                rules=mention_or_name("📜・rules"),
                news=mention_or_name("📢・announcements"),
                chat=mention_or_name("💭・chat"),
                media=mention_or_name("📸・gallery"),
                lfg=mention_or_name("🤝・lfg"),
            )
            await self._send_starter_embed(w_channel, w_cfg, custom_description=formatted_text)

        # 4. Настраиваем системные каналы самого сервера (AFK и приветствия Discord)
        edit_kwargs = {}
        if afk_channel is not None:
            edit_kwargs["afk_channel"] = afk_channel
            edit_kwargs["afk_timeout"] = 900
        if "👋・welcome" in created_channels_map:
            edit_kwargs["system_channel"] = created_channels_map["👋・welcome"]
            edit_kwargs["system_channel_flags"] = discord.SystemChannelFlags(
                join_notifications=True,
                premium_subscriptions=True,
            )

        if edit_kwargs:
            try:
                await guild.edit(**edit_kwargs, reason="Настройка системных каналов")
            except discord.HTTPException:
                pass

        # 5. Очистка старых сиротских каналов
        deleted_channels = 0
        if clean:
            for ch in guild.text_channels:
                if ch.category_id is None and ch.id != interaction.channel_id:
                    try:
                        await ch.delete(reason="Очистка старых каналов")
                        deleted_channels += 1
                        await asyncio.sleep(DELETE_PAUSE)
                    except discord.HTTPException:
                        pass

        # 6. Итоговый отчёт
        embed = discord.Embed(
            title="🏗️ Сервер успешно модернизирован!",
            description=(
                "Создана полная инфраструктура: роли с правами, форумы с тегами, "
                "приватный раздел для стаффа и кликабельная навигация."
            ),
            color=discord.Color.from_rgb(88, 101, 242),  # Фирменный Discord Blurple
        )
        embed.set_author(
            name=f"{guild.name} • Архитектор",
            icon_url=interaction.user.display_avatar.url,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🎭 Роли", value=f"`+{created_roles}`", inline=True)
        embed.add_field(name="📁 Категории", value=f"`+{created_categories}`", inline=True)
        embed.add_field(name="💬 Текстовые", value=f"`+{created_text}`", inline=True)
        embed.add_field(name="🗂️ Форумы", value=f"`+{created_forums}`", inline=True)
        embed.add_field(name="🔊 Голосовые / Сцены", value=f"`+{created_voice}`", inline=True)
        embed.add_field(
            name="🧹 Очистка",
            value=f"`-{deleted_channels}`" if clean else "`Выкл.`",
            inline=True,
        )
        embed.set_footer(text="💡 Совет: включи «Сообщество» в настройках сервера для работы Трибуны и Анонсов")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _send_starter_embed(
        self,
        channel: discord.TextChannel,
        cfg: TextChannelConfig,
        custom_description: str | None = None,
    ) -> None:
        """Вспомогательный метод для красивого оформления и закрепления первого сообщения."""
        embed = discord.Embed(
            title=cfg.first_message_title or f"#{channel.name}",
            description=custom_description or cfg.first_message,
            color=discord.Color.from_rgb(88, 101, 242),
        )
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        embed.set_footer(text=channel.guild.name)

        msg = await channel.send(embed=embed)
        if cfg.pin_first_message:
            try:
                await msg.pin(reason="Важное стартовое сообщение")
                # Удаляем системную плашку "Бот закрепил сообщение в этом канале"
                async for sys_msg in channel.history(limit=3):
                    if sys_msg.type == discord.MessageType.pins_add:
                        await sys_msg.delete()
                        break
            except discord.HTTPException:
                pass

    @app_commands.command(
        name="ресет",
        description="Сброс сервера: удалить каналы и/или роли, созданные ботом (только админы)",
    )
    @app_commands.describe(
        каналы="Удалить все каналы, форумы и категории (кроме текущего канала)",
        роли="Удалить роли, созданные ботом при /построй",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(
        self,
        interaction: discord.Interaction,
        каналы: bool = True,
        роли: bool = True,
    ) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Вызывай команду из текстового канала на сервере.", ephemeral=True
            )
            return

        if not каналы and not роли:
            await interaction.response.send_message("❌ Оба параметра выключены.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        current_channel = interaction.channel
        deleted_channels = 0
        deleted_categories = 0
        deleted_roles = 0

        if каналы:
            try:
                await guild.edit(afk_channel=None, system_channel=None)
            except discord.HTTPException:
                pass

            for ch in list(guild.channels):
                if ch.id == current_channel.id or isinstance(ch, discord.CategoryChannel):
                    continue
                try:
                    await ch.delete(reason="Ресет сервера")
                    deleted_channels += 1
                    await asyncio.sleep(DELETE_PAUSE)
                except discord.HTTPException:
                    pass

            for cat in list(guild.categories):
                if cat.id == current_channel.category_id:
                    continue
                try:
                    await cat.delete(reason="Ресет сервера")
                    deleted_categories += 1
                    await asyncio.sleep(DELETE_PAUSE)
                except discord.HTTPException:
                    pass

        if роли:
            bot_role_names = {r.name for r in ROLES_CONFIG}
            for role in list(guild.roles):
                if role.is_default() or role.managed or role.is_bot_managed():
                    continue
                if role.name not in bot_role_names:
                    continue
                try:
                    await role.delete(reason="Ресет сервера")
                    deleted_roles += 1
                    await asyncio.sleep(DELETE_PAUSE)
                except discord.HTTPException:
                    pass

        embed = discord.Embed(
            title="🧹 Ресет завершён",
            description="Сервер очищен. Можно строить заново через `/построй`.",
            color=discord.Color.from_rgb(231, 76, 60),
        )
        if каналы:
            embed.add_field(name="💬 Каналы и Форумы", value=f"`{deleted_channels}`", inline=True)
            embed.add_field(name="📁 Категории", value=f"`{deleted_categories}`", inline=True)
        if роли:
            embed.add_field(name="🎭 Роли", value=f"`{deleted_roles}`", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
        if role is not None and role not in member.roles:
            try:
                await member.add_roles(role, reason="Авто-роль новичка")
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Builder(bot))
