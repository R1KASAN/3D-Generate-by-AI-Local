from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIN_SAFE_WAL_VERSION = (3, 22, 0)


class Database:
    def __init__(
        self,
        path: Path,
        *,
        busy_timeout_ms: int = 5_000,
        sqlite_version: tuple[int, int, int] | None = None,
    ) -> None:
        if busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms cannot be negative")
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self.sqlite_version = sqlite_version or tuple(sqlite3.sqlite_version_info)

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connection() as connection:
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            await connection.executescript(schema)
            await connection.commit()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            await connection.execute("PRAGMA foreign_keys = ON")
            await connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            journal_mode = "WAL" if self.sqlite_version >= MIN_SAFE_WAL_VERSION else "DELETE"
            await connection.execute(f"PRAGMA journal_mode = {journal_mode}")
            yield connection
        except Exception:
            await connection.rollback()
            raise
        finally:
            await connection.close()
