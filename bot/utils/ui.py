"""Общий стиль карточек и безопасная обработка UI-взаимодействий."""

import logging

import discord

log = logging.getLogger(__name__)
ACCENT = 0x5B8DEF
SUCCESS = 0x35BFA3
WARNING = 0xE7AE52
MUTED = 0x747F91


def card(title: str, description: str = "", *, color: int = ACCENT) -> discord.Embed:
    embed = discord.Embed(
        title=title[:256], description=description[:4096], color=color
    )
    embed.set_footer(text="СООБЩЕСТВО • меньше суеты, больше совместных дел")
    return embed


def plain(text: str, limit: int = 1000) -> str:
    """Недоверенный текст без упоминаний и управляющей Markdown-разметки."""
    return discord.utils.escape_markdown(discord.utils.escape_mentions(text))[:limit]


async def private(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def ui_error(interaction: discord.Interaction, error: Exception) -> None:
    log.error(
        "Ошибка интерфейса на сервере %s: %s",
        interaction.guild_id,
        type(error).__name__,
    )
    try:
        await private(
            interaction,
            "Не удалось обновить карточку. Если действие уже сохранилось, "
            "его покажет кнопка «Обновить». Попробуй ещё раз чуть позже.",
        )
    except discord.HTTPException as send_error:
        log.warning("Ошибка ответа интерфейса: HTTP %s", send_error.status)


class SafeView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180) -> None:
        super().__init__(timeout=timeout)
        self.message: discord.Message | discord.InteractionMessage | None = None

    async def on_error(self, interaction, error, item) -> None:
        await ui_error(interaction, error)

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException as error:
                log.debug("Истечение карточки: HTTP %s", error.status)


class PersonalView(SafeView):
    def __init__(self, user_id: int, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await private(interaction, "Это личное меню. Открой своё через /hello.")
            return False
        return True


class SafeModal(discord.ui.Modal):
    async def on_error(self, interaction, error) -> None:
        await ui_error(interaction, error)
