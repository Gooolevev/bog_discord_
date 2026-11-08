"""Постоянный учёт объектов Discord, созданных ботом, для безопасного сброса."""

import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "builder.sqlite3"


class ResourceStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    def _execute(
        self, sql: str, parameters: tuple[int, ...] = ()
    ) -> list[tuple[int, ...]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
            return connection.execute(sql, parameters).fetchall()

    async def initialize(self) -> None:
        await asyncio.to_thread(
            self._execute,
            "CREATE TABLE IF NOT EXISTS resources "
            "(guild_id INTEGER, resource_id INTEGER, PRIMARY KEY (guild_id, resource_id))",
        )

    async def ids(self, guild_id: int) -> set[int]:
        rows = await asyncio.to_thread(
            self._execute,
            "SELECT resource_id FROM resources WHERE guild_id = ?",
            (guild_id,),
        )
        return {row[0] for row in rows}

    async def add(self, guild_id: int, resource_id: int) -> None:
        await asyncio.to_thread(
            self._execute,
            "INSERT OR IGNORE INTO resources VALUES (?, ?)",
            (guild_id, resource_id),
        )

    async def remove(self, guild_id: int, resource_id: int) -> None:
        await asyncio.to_thread(
            self._execute,
            "DELETE FROM resources WHERE guild_id = ? AND resource_id = ?",
            (guild_id, resource_id),
        )
