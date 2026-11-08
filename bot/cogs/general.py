"""Личное меню, информация о сообществе и существующие команды."""

import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.community import PublishModal
from bot.utils.ui import PersonalView, SafeView, card, plain, private


def home_embed(section: str = "home") -> discord.Embed:
    sections = {
        "home": (
            "ТВОЙ СЕРВЕР · Всё под рукой",
            "Собрать людей, принять решение или зайти в Minecraft — начни с кнопок ниже.\n\nЭто личное меню. Опубликованные опросы и сборы увидит весь канал.",
        ),
        "together": (
            "ВМЕСТЕ · От идеи к делу",
            "**Опрос** — 2–6 вариантов, один голос на человека, изменение ответа и итог по таймеру.\n\n**Сбор** — запись в команду с лимитом мест и временем начала. Организатор уже в списке.\n\nСоздавай через кнопки ниже или команды `/poll` и `/сбор`.",
        ),
        "minecraft": (
            "MINECRAFT · Встречаемся в мире",
            "Кнопка Minecraft открывает статус, адрес подключения и список игроков из ответа сервера.\n\n`/server` публикует такую панель в канале. Обновление доступно прямо в карточке.",
        ),
        "tools": (
            "ИНСТРУМЕНТЫ · Без лишних движений",
            "`/userinfo` — профиль участника\n`/serverinfo` — сообщество в цифрах\n`/avatar` — аватар в полном размере\n`/choose` — случайный выбор из вариантов\n`/ai` — вопрос помощнику, если настроен ключ\n`/ping` — связь с ботом",
        ),
        "admin": (
            "ОРГАНИЗАТОРУ · Настройка сообщества",
            "`/построй` — создать структуру сервера\n`/ресет` — просмотреть и подтвердить удаление объектов бота\n`/мониторинг` — проверить наблюдение за Minecraft\n\nАдминистративные команды проверяют права. Опрос или сбор может завершить автор либо участник с правом управления сообщениями.",
        ),
    }
    title, description = sections[section]
    return card(title, description)


class HomeView(PersonalView):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(user_id)
        self.bot = bot

    @discord.ui.select(
        placeholder="Что хочется сделать?",
        row=0,
        options=[
            discord.SelectOption(label="Главная", value="home", emoji="🏠"),
            discord.SelectOption(
                label="Общие решения и сбор команды", value="together", emoji="🤝"
            ),
            discord.SelectOption(label="Minecraft", value="minecraft", emoji="⛏️"),
            discord.SelectOption(label="Полезные команды", value="tools", emoji="🧭"),
            discord.SelectOption(label="Организатору", value="admin", emoji="⚙️"),
        ],
    )
    async def section(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        for option in select.options:
            option.default = option.value == select.values[0]
        await interaction.response.edit_message(
            embed=home_embed(select.values[0]), view=self
        )

    async def open_modal(self, interaction: discord.Interaction, kind: str) -> None:
        cog = self.bot.get_cog("Community")
        if cog is None:
            await private(interaction, "Раздел сообщества временно недоступен.")
            return
        if interaction.guild_id is None:
            await private(
                interaction,
                "Открой /hello в канале сервера, чтобы опубликовать карточку.",
            )
            return
        default = await cog.poll_minutes(interaction.guild_id) if kind == "poll" else 60
        await interaction.response.send_modal(PublishModal(cog, kind, default))

    @discord.ui.button(
        label="Создать опрос", emoji="🗳️", style=discord.ButtonStyle.primary, row=1
    )
    async def poll(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.open_modal(interaction, "poll")

    @discord.ui.button(
        label="Собрать команду", emoji="🙌", style=discord.ButtonStyle.success, row=1
    )
    async def party(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.open_modal(interaction, "party")

    @discord.ui.button(
        label="Minecraft", emoji="⛏️", style=discord.ButtonStyle.secondary, row=1
    )
    async def minecraft(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        cog = self.bot.get_cog("Minecraft")
        if cog is None:
            await private(interaction, "Панель Minecraft временно недоступна.")
            return
        await cog.show(interaction, ephemeral=True)


class RPSView(SafeView):
    """Интерактивные кнопки для игры в Камень, Ножницы, Бумага"""

    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.user = user
        self.finished = False

    async def play(self, interaction: discord.Interaction, user_choice: str):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Это не твоя игра! Вызови свою через `/rps`.", ephemeral=True
            )
            return

        if self.finished:
            await private(interaction, "Эта партия уже завершена. Новая — через /rps.")
            return
        self.finished = True
        choices = {"Камень": "🪨", "Ножницы": "✂️", "Бумага": "📄"}
        bot_choice = random.choice(list(choices.keys()))

        if user_choice == bot_choice:
            result = "🤝 Ничья!"
            color = discord.Color.gold()
        elif (
            (user_choice == "Камень" and bot_choice == "Ножницы")
            or (user_choice == "Ножницы" and bot_choice == "Бумага")
            or (user_choice == "Бумага" and bot_choice == "Камень")
        ):
            result = "🎉 Ты победил(а)!"
            color = discord.Color.green()
        else:
            result = "💀 Бот победил!"
            color = discord.Color.red()

        embed = discord.Embed(title="Камень, Ножницы, Бумага", color=color)
        embed.add_field(
            name="Твой выбор",
            value=f"{choices[user_choice]} {user_choice}",
            inline=True,
        )
        embed.add_field(
            name="Выбор бота", value=f"{choices[bot_choice]} {bot_choice}", inline=True
        )
        embed.add_field(name="Результат", value=f"**{result}**", inline=False)

        # Отключаем кнопки после нажатия
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(content=None, embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Камень", emoji="🪨", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Камень")

    @discord.ui.button(label="Ножницы", emoji="✂️", style=discord.ButtonStyle.primary)
    async def scissors(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.play(interaction, "Ножницы")

    @discord.ui.button(label="Бумага", emoji="📄", style=discord.ButtonStyle.primary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Бумага")


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._views: set[SafeView] = set()

    def remember(self, view: SafeView) -> None:
        self._views = {item for item in self._views if not item.is_finished()}
        self._views.add(view)

    async def cog_unload(self) -> None:
        for view in self._views:
            view.stop()
        self._views.clear()

    @app_commands.command(name="ping", description="Проверить задержку бота")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong! 🏓 {round(self.bot.latency * 1000)} мс"
        )

    @app_commands.command(
        name="hello",
        description="Открыть личное меню: опросы, сбор команды и Minecraft",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def hello(self, interaction: discord.Interaction):
        view = HomeView(self.bot, interaction.user.id)
        self.remember(view)
        await interaction.response.send_message(
            embed=home_embed(), view=view, ephemeral=True
        )
        view.message = await interaction.original_response()

    @app_commands.command(name="roll", description="Кинуть кубик")
    @app_commands.describe(грани="Сколько граней у кубика (по умолчанию 6)")
    async def roll(
        self,
        interaction: discord.Interaction,
        грани: app_commands.Range[int, 2, 1000] = 6,
    ):
        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} выбросил(а) **{random.randint(1, грани)}** (d{грани})"
        )

    @app_commands.command(name="coin", description="Подбросить монетку")
    async def coin(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🪙 {random.choice(['Орёл!', 'Решка!'])}"
        )

    @app_commands.command(
        name="random_user", description="Выбрать случайного участника сервера"
    )
    async def random_user(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Команда работает только на сервере.", ephemeral=True
            )
            return
        members = [m for m in guild.members if not m.bot]
        if not members:
            await interaction.response.send_message(
                "❌ На сервере нет живых участников.", ephemeral=True
            )
            return
        member = random.choice(members)
        await interaction.response.send_message(
            f"🎯 Случайный выбор пал на {member.mention}! 👋"
        )

    @app_commands.command(name="choose", description="Случайно выбрать из вариантов")
    @app_commands.describe(варианты="Варианты через запятую: крипер, зомби, скелет")
    async def choose(
        self,
        interaction: discord.Interaction,
        варианты: app_commands.Range[str, 1, 1900],
    ):
        options = [o.strip() for o in варианты.split(",") if o.strip()]
        if len(options) < 2:
            await interaction.response.send_message(
                "Нужно минимум 2 варианта через запятую!", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"🤔 Я выбираю: **{random.choice(options)}**"
        )

    # --- НОВЫЕ КОМАНДЫ ---

    @app_commands.command(name="8ball", description="Задать вопрос магическому шару")
    @app_commands.describe(вопрос="Твой вопрос, на который можно ответить Да/Нет")
    async def eight_ball(
        self, interaction: discord.Interaction, вопрос: app_commands.Range[str, 1, 1024]
    ):
        answers = [
            "Бесспорно ✅",
            "Предрешено ✅",
            "Никаких сомнений ✅",
            "Определённо да ✅",
            "Пока не ясно, попробуй снова 🔄",
            "Спроси позже ⏳",
            "Лучше не рассказывать 🤫",
            "Даже не думай ❌",
            "Мой ответ — нет ❌",
            "Весьма сомнительно 🤨",
            "Перспективы не очень 😬",
        ]
        embed = discord.Embed(title="🎱 Магический шар", color=discord.Color.purple())
        embed.add_field(name="Вопрос:", value=вопрос, inline=False)
        embed.add_field(
            name="Ответ:", value=f"**{random.choice(answers)}**", inline=False
        )
        embed.set_footer(
            text=f"Спросил(а): {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="rps", description="Сыграть с ботом в Камень, Ножницы, Бумага"
    )
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user)
        self.remember(view)
        await interaction.response.send_message("Выбирай свой ход:", view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="avatar", description="Показать аватарку пользователя")
    @app_commands.describe(пользователь="Чью аватарку показать (по умолчанию — твою)")
    async def avatar(
        self,
        interaction: discord.Interaction,
        пользователь: discord.Member | None = None,
    ):
        target = пользователь or interaction.user
        embed = card(f"ПРОФИЛЬ · {plain(target.display_name, 80)}")
        embed.set_image(url=target.display_avatar.with_size(1024).url)
        embed.add_field(
            name="Ссылка", value=f"[Открыть оригинал]({target.display_avatar.url})"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="userinfo", description="Информация об участнике сервера"
    )
    @app_commands.describe(пользователь="О ком узнать информацию")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        пользователь: discord.Member | None = None,
    ):
        target = пользователь or interaction.user
        if isinstance(target, discord.Member):
            roles = [role.mention for role in target.roles if role.name != "@everyone"]
        else:
            roles = []  # у User (ЛС) нет ролей сервера
        roles_str = ", ".join(roles) if roles else "Нет ролей"

        embed = card(f"ПРОФИЛЬ · {plain(target.display_name, 80)}")
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👤 Имя аккаунта", value=f"`{target.name}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{target.id}`", inline=True)
        embed.add_field(
            name="🤖 Бот?", value="Да" if target.bot else "Нет", inline=True
        )
        embed.add_field(
            name="📅 Аккаунт создан",
            value=discord.utils.format_dt(target.created_at, style="D"),
            inline=True,
        )
        if isinstance(target, discord.Member) and target.joined_at:
            embed.add_field(
                name="📥 Зашёл на сервер",
                value=discord.utils.format_dt(target.joined_at, style="D"),
                inline=True,
            )
            embed.add_field(
                name=f"🎭 Роли ({len(roles)})", value=roles_str[:1024], inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Информация о сервере")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Команда работает только на сервере.", ephemeral=True
            )
            return

        bots = sum(1 for m in guild.members if m.bot)
        humans = (guild.member_count or 0) - bots

        embed = card(f"СООБЩЕСТВО · {plain(guild.name, 100)}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="👑 Владелец",
            value=guild.owner.mention if guild.owner else "Неизвестно",
            inline=True,
        )
        embed.add_field(name="🆔 ID сервера", value=f"`{guild.id}`", inline=True)
        embed.add_field(
            name="📅 Создан",
            value=discord.utils.format_dt(guild.created_at, style="D"),
            inline=True,
        )
        embed.add_field(
            name="👥 Участники",
            value=f"Всего: **{guild.member_count}**\nЛюдей: **{humans}** | Ботов: **{bots}**",
            inline=True,
        )
        embed.add_field(
            name="💬 Каналы",
            value=f"Текстовых: **{len(guild.text_channels)}**\nГолосовых: **{len(guild.voice_channels)}**",
            inline=True,
        )
        embed.add_field(
            name="🚀 Бусты",
            value=f"Уровень {guild.premium_tier} ({guild.premium_subscription_count} бустов)",
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="poll",
        description="Голосование с вариантами, кнопками и итогами по таймеру",
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(
        вопрос="Тема голосования",
        варианты="2–6 ответов через ; (по умолчанию: За; Против)",
        минут="Через сколько минут подвести итоги",
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        вопрос: app_commands.Range[str, 1, 4092],
        варианты: app_commands.Range[str, 1, 500] | None = None,
        минут: app_commands.Range[int, 1, 1440] | None = None,
    ):
        cog = self.bot.get_cog("Community")
        if cog is None:
            await private(interaction, "Голосования временно недоступны.")
            return
        await cog.publish(interaction, "poll", вопрос, варианты, minutes=минут)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
