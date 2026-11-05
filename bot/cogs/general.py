"""Простые развлекательные команды."""

import random

import discord
from discord import app_commands
from discord.ext import commands


class RPSView(discord.ui.View):
    """Интерактивные кнопки для игры в Камень, Ножницы, Бумага"""
    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.user = user

    async def play(self, interaction: discord.Interaction, user_choice: str):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Это не твоя игра! Вызови свою через `/rps`.", ephemeral=True)
            return

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
        embed.add_field(name="Твой выбор", value=f"{choices[user_choice]} {user_choice}", inline=True)
        embed.add_field(name="Выбор бота", value=f"{choices[bot_choice]} {bot_choice}", inline=True)
        embed.add_field(name="Результат", value=f"**{result}**", inline=False)

        # Отключаем кнопки после нажатия
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(content=None, embed=embed, view=self)

    @discord.ui.button(label="Камень", emoji="🪨", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Камень")

    @discord.ui.button(label="Ножницы", emoji="✂️", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Ножницы")

    @discord.ui.button(label="Бумага", emoji="📄", style=discord.ButtonStyle.primary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Бумага")


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Проверить задержку бота")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! 🏓 {round(self.bot.latency * 1000)} мс")

    @app_commands.command(name="hello", description="Поприветствовать бота")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Привет, {interaction.user.mention}!")

    @app_commands.command(name="roll", description="Кинуть кубик")
    @app_commands.describe(грани="Сколько граней у кубика (по умолчанию 6)")
    async def roll(self, interaction: discord.Interaction, грани: app_commands.Range[int, 2, 1000] = 6):
        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} выбросил(а) **{random.randint(1, грани)}** (d{грани})"
        )

    @app_commands.command(name="coin", description="Подбросить монетку")
    async def coin(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🪙 {random.choice(['Орёл!', 'Решка!'])}")

    @app_commands.command(name="random_user", description="Выбрать случайного участника сервера")
    async def random_user(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Команда работает только на сервере.", ephemeral=True)
            return
        members = [m for m in guild.members if not m.bot]
        if not members:
            await interaction.response.send_message("❌ На сервере нет живых участников.", ephemeral=True)
            return
        member = random.choice(members)
        await interaction.response.send_message(f"🎯 Случайный выбор пал на {member.mention}! 👋")

    @app_commands.command(name="choose", description="Случайно выбрать из вариантов")
    @app_commands.describe(варианты="Варианты через запятую: крипер, зомби, скелет")
    async def choose(self, interaction: discord.Interaction, варианты: str):
        options = [o.strip() for o in варианты.split(",") if o.strip()]
        if len(options) < 2:
            await interaction.response.send_message("Нужно минимум 2 варианта через запятую!", ephemeral=True)
            return
        await interaction.response.send_message(f"🤔 Я выбираю: **{random.choice(options)}**")

    # --- НОВЫЕ КОМАНДЫ ---

    @app_commands.command(name="8ball", description="Задать вопрос магическому шару")
    @app_commands.describe(вопрос="Твой вопрос, на который можно ответить Да/Нет")
    async def eight_ball(self, interaction: discord.Interaction, вопрос: str):
        answers = [
            "Бесспорно ✅", "Предрешено ✅", "Никаких сомнений ✅", "Определённо да ✅",
            "Пока не ясно, попробуй снова 🔄", "Спроси позже ⏳", "Лучше не рассказывать 🤫",
            "Даже не думай ❌", "Мой ответ — нет ❌", "Весьма сомнительно 🤨", "Перспективы не очень 😬"
        ]
        embed = discord.Embed(title="🎱 Магический шар", color=discord.Color.purple())
        embed.add_field(name="Вопрос:", value=вопрос, inline=False)
        embed.add_field(name="Ответ:", value=f"**{random.choice(answers)}**", inline=False)
        embed.set_footer(text=f"Спросил(а): {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Сыграть с ботом в Камень, Ножницы, Бумага")
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user)
        await interaction.response.send_message("Выбирай свой ход:", view=view)

    @app_commands.command(name="avatar", description="Показать аватарку пользователя")
    @app_commands.describe(пользователь="Чью аватарку показать (по умолчанию — твою)")
    async def avatar(self, interaction: discord.Interaction, пользователь: discord.Member | None = None):
        target = пользователь or interaction.user
        embed = discord.Embed(
            title=f"Аватар {target.display_name}",
            color=target.color if target.color != discord.Color.default() else discord.Color.blurple()
        )
        embed.set_image(url=target.display_avatar.with_size(1024).url)
        embed.add_field(name="Ссылка", value=f"[Открыть оригинал]({target.display_avatar.url})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Информация об участнике сервера")
    @app_commands.describe(пользователь="О ком узнать информацию")
    async def userinfo(self, interaction: discord.Interaction, пользователь: discord.Member | None = None):
        target = пользователь or interaction.user
        if isinstance(target, discord.Member):
            roles = [role.mention for role in target.roles if role.name != "@everyone"]
        else:
            roles = []  # у User (ЛС) нет ролей сервера
        roles_str = ", ".join(roles) if roles else "Нет ролей"

        embed = discord.Embed(
            title=f"Информация о {target.display_name}",
            color=target.color if target.color != discord.Color.default() else discord.Color.blurple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👤 Имя аккаунта", value=f"`{target.name}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="🤖 Бот?", value="Да" if target.bot else "Нет", inline=True)
        embed.add_field(
            name="📅 Аккаунт создан",
            value=discord.utils.format_dt(target.created_at, style="D"),
            inline=True
        )
        if isinstance(target, discord.Member) and target.joined_at:
            embed.add_field(
                name="📥 Зашёл на сервер",
                value=discord.utils.format_dt(target.joined_at, style="D"),
                inline=True
            )
            embed.add_field(name=f"🎭 Роли ({len(roles)})", value=roles_str[:1024], inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Информация о сервере")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Команда работает только на сервере.", ephemeral=True)
            return

        bots = sum(1 for m in guild.members if m.bot)
        humans = (guild.member_count or 0) - bots

        embed = discord.Embed(title=f"📊 Сервер {guild.name}", color=discord.Color.teal())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Владелец", value=guild.owner.mention if guild.owner else "Неизвестно", inline=True)
        embed.add_field(name="🆔 ID сервера", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Создан", value=discord.utils.format_dt(guild.created_at, style="D"), inline=True)
        embed.add_field(name="👥 Участники", value=f"Всего: **{guild.member_count}**\nЛюдей: **{humans}** | Ботов: **{bots}**", inline=True)
        embed.add_field(
            name="💬 Каналы",
            value=f"Текстовых: **{len(guild.text_channels)}**\nГолосовых: **{len(guild.voice_channels)}**",
            inline=True
        )
        embed.add_field(name="🚀 Бусты", value=f"Уровень {guild.premium_tier} ({guild.premium_subscription_count} бустов)", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Создать быстрое голосование (Да/Нет)")
    @app_commands.describe(вопрос="Тема голосования")
    async def poll(self, interaction: discord.Interaction, вопрос: str):
        embed = discord.Embed(
            title="📊 Голосование",
            description=f"**{вопрос}**",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Автор опроса: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("👍")
        await message.add_reaction("👎")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
