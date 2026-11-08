"""Закрытый локальный API панели. Discord-токен не покидает Python-процесс."""

import hmac
import logging
import math

import discord
from aiohttp import web

log = logging.getLogger(__name__)


def snowflake(value) -> int:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdigit()
        or not 1 <= int(value) < 2**63
    ):
        raise web.HTTPBadRequest(text="Некорректный идентификатор Discord")
    return int(value)


def create_dashboard_app(bot, secret: str) -> web.Application:
    if len(secret) < 32:
        raise ValueError("BOT_API_SECRET должен содержать не менее 32 символов")

    @web.middleware
    async def authenticate(request, handler):
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied.encode(), f"Bearer {secret}".encode()):
            raise web.HTTPUnauthorized(text="Нет доступа")
        if not bot.is_ready() or bot.is_closed():
            raise web.HTTPServiceUnavailable(text="Бот пока не подключён к Discord")
        try:
            return await handler(request)
        except discord.Forbidden:
            raise web.HTTPForbidden(text="Недостаточно прав Discord") from None
        except discord.NotFound:
            raise web.HTTPNotFound(text="Сервер или участник недоступен") from None
        except discord.HTTPException as error:
            log.warning("Discord API панели: HTTP %s", error.status)
            raise web.HTTPServiceUnavailable(
                text="Discord временно недоступен"
            ) from None
        except web.HTTPException:
            raise
        except Exception as error:  # noqa: BLE001 — HTTP-граница, без приватных деталей
            log.error("API панели: %s", type(error).__name__)
            raise web.HTTPInternalServerError(
                text="Не удалось обработать запрос"
            ) from None

    app = web.Application(middlewares=[authenticate], client_max_size=16384)

    async def managed_guild(guild_id: int, user_id: int):
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise web.HTTPNotFound(text="Бот не установлен на этом сервере")
        # Получаем актуальное членство, роли и владельца, а не доверяем браузеру
        # или давно открытой странице панели.
        current = await bot.fetch_guild(guild_id)
        member = await guild.fetch_member(user_id)
        roles = await guild.fetch_roles()
        member_roles = {role.id for role in member.roles}
        permissions = 0
        for role in roles:
            if role.id == guild.id or role.id in member_roles:
                permissions |= role.permissions.value
        if current.owner_id != user_id and not permissions & (8 | 32):
            raise web.HTTPForbidden(text="Нужно право управления сервером")
        return guild

    def summary(guild):
        return {
            "id": str(guild.id),
            "name": guild.name,
            "icon": str(guild.icon.url) if guild.icon else None,
            "member_count": guild.member_count,
        }

    async def list_guilds(request):
        try:
            body = await request.json()
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(text="Некорректный JSON") from None
        if (
            not isinstance(body, dict)
            or not isinstance(body.get("guild_ids"), list)
            or len(body["guild_ids"]) > 200
        ):
            raise web.HTTPBadRequest(text="Некорректный список серверов")
        user_id = snowflake(body.get("user_id"))
        result = []
        for value in dict.fromkeys(snowflake(value) for value in body["guild_ids"]):
            try:
                guild = await managed_guild(value, user_id)
            except (
                web.HTTPForbidden,
                web.HTTPNotFound,
                discord.NotFound,
                discord.Forbidden,
            ):
                continue
            result.append(summary(guild))
        return web.json_response({"guilds": result})

    async def details(request):
        guild = await managed_guild(
            snowflake(request.match_info["guild_id"]),
            snowflake(request.query.get("user_id")),
        )
        monitor = bot.get_cog("Monitor")
        legacy = monitor._monitor_channel() if monitor is not None else None
        legacy_id = (
            legacy.id if legacy is not None and legacy.guild.id == guild.id else 0
        )
        settings = await bot.settings.get(guild.id, legacy_id)
        channels = [
            {"id": str(channel.id), "name": channel.name}
            for channel in guild.text_channels
            if guild.me is not None
            and channel.permissions_for(guild.me).view_channel
            and channel.permissions_for(guild.me).send_messages
            and channel.permissions_for(guild.me).embed_links
        ]
        latency = bot.latency
        return web.json_response(
            {
                "guild": summary(guild),
                "settings": {
                    **settings,
                    "guild_id": str(guild.id),
                    "monitor_channel_id": str(settings["monitor_channel_id"]),
                },
                "channels": channels,
                "bot": {
                    "ready": bot.is_ready(),
                    "latency_ms": round(latency * 1000)
                    if math.isfinite(latency)
                    else None,
                },
            }
        )

    async def update(request):
        guild = await managed_guild(
            snowflake(request.match_info["guild_id"]),
            snowflake(request.query.get("user_id")),
        )
        try:
            body = await request.json()
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(text="Некорректный JSON") from None
        if not isinstance(body, dict) or set(body) != {
            "monitor_enabled",
            "monitor_channel_id",
            "poll_minutes",
        }:
            raise web.HTTPBadRequest(text="Некорректные настройки")
        channel_id = (
            0
            if body["monitor_channel_id"] == "0"
            else snowflake(body["monitor_channel_id"])
        )
        if channel_id:
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel) or guild.me is None:
                raise web.HTTPBadRequest(text="Выбери текстовый канал этого сервера")
            permissions = channel.permissions_for(guild.me)
            if not (
                permissions.view_channel
                and permissions.send_messages
                and permissions.embed_links
            ):
                raise web.HTTPBadRequest(text="Боту не хватает прав в выбранном канале")
        try:
            saved = await bot.settings.save(
                guild.id, body["monitor_enabled"], channel_id, body["poll_minutes"]
            )
        except ValueError as error:
            raise web.HTTPBadRequest(text=str(error)) from None
        return web.json_response(
            {
                "settings": {
                    **saved,
                    "guild_id": str(guild.id),
                    "monitor_channel_id": str(channel_id),
                }
            }
        )

    app.router.add_post("/guilds", list_guilds)
    app.router.add_get("/guilds/{guild_id}", details)
    app.router.add_put("/guilds/{guild_id}", update)
    return app
