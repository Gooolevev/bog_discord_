"""Настройки отдельных серверов в существующей базе сообщества."""

import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path

from bot.utils.community import DEFAULT_PATH


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else DEFAULT_PATH

    async def _run(self, operation, *args):
        def execute():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
                db.row_factory = sqlite3.Row
                return operation(db, *args)

        return await asyncio.to_thread(execute)

    async def initialize(self) -> None:
        await self._run(
            lambda db: (
                db.execute(
                    "CREATE TABLE IF NOT EXISTS guild_settings (guild_id INTEGER PRIMARY KEY, "
                    "monitor_enabled INTEGER NOT NULL DEFAULT 0, monitor_channel_id INTEGER NOT NULL DEFAULT 0, "
                    "poll_minutes INTEGER NOT NULL DEFAULT 60 CHECK(poll_minutes BETWEEN 1 AND 1440))"
                ).rowcount
            )
        )

    async def get(self, guild_id: int, legacy_channel_id: int = 0) -> dict:
        def read(db):
            row = db.execute(
                "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
            ).fetchone()
            return (
                dict(row)
                if row
                else {
                    "guild_id": guild_id,
                    "monitor_enabled": bool(legacy_channel_id),
                    "monitor_channel_id": legacy_channel_id,
                    "poll_minutes": 60,
                }
            )

        result = await self._run(read)
        result["monitor_enabled"] = bool(result["monitor_enabled"])
        return result

    async def save(
        self, guild_id: int, enabled: bool, channel_id: int, minutes: int
    ) -> dict:
        if (
            type(enabled) is not bool
            or type(channel_id) is not int
            or type(minutes) is not int
        ):
            raise ValueError("Некорректные типы настроек")
        if (
            channel_id < 0
            or channel_id >= 2**63
            or not 1 <= minutes <= 1440
            or (enabled and not channel_id)
        ):
            raise ValueError("Проверь канал и длительность опросов (1–1440 минут)")
        await self._run(
            lambda db: (
                db.execute(
                    "INSERT INTO guild_settings VALUES (?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET "
                    "monitor_enabled = excluded.monitor_enabled, monitor_channel_id = excluded.monitor_channel_id, "
                    "poll_minutes = excluded.poll_minutes",
                    (guild_id, enabled, channel_id, minutes),
                ).rowcount
            )
        )
        return await self.get(guild_id)

    async def all(self) -> list[dict]:
        return await self._run(
            lambda db: [dict(row) for row in db.execute("SELECT * FROM guild_settings")]
        )
