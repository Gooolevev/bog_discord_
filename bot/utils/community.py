"""Атомарное хранение голосований и сборов. SQLite работает вне event loop."""

import asyncio
import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "community.sqlite3"


class BoardError(Exception):
    """Ожидаемый отказ, который можно показать участнику."""


@dataclass
class Board:
    id: int
    guild_id: int
    channel_id: int
    message_id: int | None
    author_id: int
    kind: str
    title: str
    options: list[str]
    capacity: int
    ends_at: int
    created_at: float
    closed: bool
    published_closed: bool
    votes: dict[int, int]


def poll_options(text: str | None) -> list[str]:
    options = [value.strip() for value in text.split(";")] if text else ["За", "Против"]
    if not 2 <= len(options) <= 6 or any(
        not value or len(value) > 80 for value in options
    ):
        raise BoardError("Нужны 2–6 вариантов через ;, каждый от 1 до 80 символов.")
    if len({value.casefold() for value in options}) != len(options):
        raise BoardError("Варианты ответа должны отличаться.")
    return options


class CommunityStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    async def _run(self, operation, *args):
        return await asyncio.to_thread(self._transaction, operation, args)

    def _transaction(self, operation, args):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                return operation(connection, *args)

    async def initialize(self) -> None:
        def operation(db):
            db.execute(
                "CREATE TABLE IF NOT EXISTS boards ("
                "id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, "
                "channel_id INTEGER NOT NULL, message_id INTEGER UNIQUE, "
                "author_id INTEGER NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, "
                "options TEXT NOT NULL, capacity INTEGER NOT NULL, ends_at INTEGER NOT NULL, created_at REAL NOT NULL, "
                "closed INTEGER NOT NULL DEFAULT 0, published_closed INTEGER NOT NULL DEFAULT 0)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS entries ("
                "board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE, "
                "user_id INTEGER NOT NULL, choice INTEGER NOT NULL, changed_at REAL NOT NULL, "
                "PRIMARY KEY(board_id, user_id))"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS boards_due ON boards(published_closed, ends_at)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS boards_author ON boards(guild_id, author_id, created_at)"
            )
            # Неприкреплённая карточка могла остаться после аварии во время публикации.
            db.execute("DELETE FROM boards WHERE message_id IS NULL")

        await self._run(operation)

    @staticmethod
    def _read(db, board_id: int, guild_id: int) -> Board:
        row = db.execute(
            "SELECT * FROM boards WHERE id = ? AND guild_id = ?", (board_id, guild_id)
        ).fetchone()
        if row is None:
            raise BoardError("Эта карточка больше недоступна на этом сервере.")
        votes = dict(
            db.execute(
                "SELECT user_id, choice FROM entries WHERE board_id = ? AND choice >= 0",
                (board_id,),
            ).fetchall()
        )
        values = dict(row)
        values["options"] = json.loads(values["options"])
        return Board(**values, votes=votes)

    async def create(
        self,
        guild_id: int,
        channel_id: int,
        author_id: int,
        kind: str,
        title: str,
        options: list[str],
        capacity: int,
        minutes: int,
    ) -> Board:
        title = title.strip()
        if kind not in ("poll", "party") or not title or len(title) > 4092:
            raise BoardError("Тема должна содержать от 1 до 4092 символов.")
        if not 1 <= minutes <= 1440:
            raise BoardError("Укажи время от 1 до 1440 минут.")
        if kind == "poll":
            options = poll_options(";".join(options))
        elif not 2 <= capacity <= 50 or len(title) > 180:
            raise BoardError("Для сбора нужны 2–50 мест и тема до 180 символов.")

        def operation(db):
            now = time.time()
            active = db.execute(
                "SELECT COUNT(*) FROM boards WHERE guild_id = ? AND closed = 0 AND ends_at > ?",
                (guild_id, now),
            ).fetchone()[0]
            if active >= 20:
                raise BoardError(
                    "На сервере уже 20 активных карточек. Заверши одну из них."
                )
            recent = db.execute(
                "SELECT 1 FROM boards WHERE guild_id = ? AND author_id = ? "
                "AND created_at > ? LIMIT 1",
                (guild_id, author_id, now - 15),
            ).fetchone()
            if recent:
                raise BoardError("Между публикациями нужно подождать 15 секунд.")
            cursor = db.execute(
                "INSERT INTO boards (guild_id, channel_id, author_id, kind, title, "
                "options, capacity, ends_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    guild_id,
                    channel_id,
                    author_id,
                    kind,
                    title,
                    json.dumps(options, ensure_ascii=False),
                    capacity,
                    int(now) + minutes * 60,
                    now,
                ),
            )
            board_id = cursor.lastrowid
            if kind == "party":
                db.execute(
                    "INSERT INTO entries VALUES (?, ?, 0, 0)", (board_id, author_id)
                )
            return self._read(db, board_id, guild_id)

        return await self._run(operation)

    async def attach(self, board: Board, message_id: int) -> None:
        await self._run(
            lambda db: (
                db.execute(
                    "UPDATE boards SET message_id = ? WHERE id = ? AND guild_id = ?",
                    (message_id, board.id, board.guild_id),
                ).rowcount
            )
        )

    async def discard(self, board: Board) -> None:
        await self._run(
            lambda db: (
                db.execute(
                    "DELETE FROM boards WHERE id = ? AND guild_id = ? AND message_id IS NULL",
                    (board.id, board.guild_id),
                ).rowcount
            )
        )

    async def get(self, board_id: int, guild_id: int) -> Board:
        return await self._run(self._read, board_id, guild_id)

    async def for_message(self, guild_id: int, message_id: int) -> Board:
        def operation(db):
            row = db.execute(
                "SELECT id FROM boards WHERE guild_id = ? AND message_id = ?",
                (guild_id, message_id),
            ).fetchone()
            if row is None:
                raise BoardError("Эта карточка больше недоступна.")
            return self._read(db, row[0], guild_id)

        return await self._run(operation)

    async def act(
        self,
        board_id: int,
        guild_id: int,
        user_id: int,
        choice: int,
        *,
        close: bool = False,
        moderator: bool = False,
    ) -> Board:
        def operation(db):
            now = time.time()
            board = self._read(db, board_id, guild_id)
            if board.closed or now >= board.ends_at:
                raise BoardError("Карточка завершена. Новые ответы уже не принимаются.")
            if close:
                if user_id != board.author_id and not moderator:
                    raise BoardError(
                        "Завершить может автор или участник с правом управления сообщениями."
                    )
                db.execute("UPDATE boards SET closed = 1 WHERE id = ?", (board_id,))
            else:
                maximum = len(board.options) if board.kind == "poll" else 1
                if choice < -1 or choice >= maximum:
                    raise BoardError("Такого варианта нет в карточке.")
                previous = db.execute(
                    "SELECT choice, changed_at FROM entries WHERE board_id = ? AND user_id = ?",
                    (board_id, user_id),
                ).fetchone()
                if previous and previous[0] == choice:
                    raise BoardError("Этот ответ уже сохранён.")
                if previous and now - previous[1] < 2:
                    raise BoardError("Подожди 2 секунды перед следующим изменением.")
                if choice == -1 and (previous is None or previous[0] == -1):
                    raise BoardError("У тебя ещё нет записи в этой карточке.")
                if (
                    board.kind == "party"
                    and choice == 0
                    and len(board.votes) >= board.capacity
                ):
                    raise BoardError(
                        "Все места заняты. Попробуй, когда кто-нибудь выйдет."
                    )
                db.execute(
                    "INSERT INTO entries VALUES (?, ?, ?, ?) ON CONFLICT(board_id, user_id) "
                    "DO UPDATE SET choice = excluded.choice, changed_at = excluded.changed_at",
                    (board_id, user_id, choice, now),
                )
            return self._read(db, board_id, guild_id)

        return await self._run(operation)

    async def due(self) -> list[Board]:
        def operation(db):
            rows = db.execute(
                "SELECT id, guild_id FROM boards WHERE published_closed = 0 "
                "AND message_id IS NOT NULL AND (closed = 1 OR ends_at <= ?)",
                (time.time(),),
            ).fetchall()
            return [self._read(db, row[0], row[1]) for row in rows]

        return await self._run(operation)

    async def published(self, board: Board) -> None:
        await self._run(
            lambda db: (
                db.execute(
                    "UPDATE boards SET closed = 1, published_closed = 1 WHERE id = ? AND guild_id = ?",
                    (board.id, board.guild_id),
                ).rowcount
            )
        )
