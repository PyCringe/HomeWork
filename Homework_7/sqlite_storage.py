import asyncio
import json

import aiosqlite

from data_storage import DataStorage


class SQLiteStorage(DataStorage):
    def __init__(self, db_path: str, batch_size: int = 10):
        self.db_path = db_path
        self.batch_size = batch_size
        self._conn: aiosqlite.Connection | None = None
        self._buffer: list[dict] = []
        self._lock = asyncio.Lock()

    async def init_db(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                text TEXT,
                links TEXT,
                metadata TEXT,
                crawled_at TEXT,
                status_code INTEGER,
                content_type TEXT
            )
            """
        )
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status_code)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_crawled_at ON pages(crawled_at)")
        await self._conn.commit()

    async def save(self, data: dict):
        if self._conn is None:
            await self.init_db()
        async with self._lock:
            self._buffer.append(data)
            if len(self._buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        if not self._buffer:
            return
        rows = [
            (
                d["url"],
                d.get("title"),
                d.get("text"),
                json.dumps(d.get("links", []), ensure_ascii=False),
                json.dumps(d.get("metadata", {}), ensure_ascii=False),
                d.get("crawled_at"),
                d.get("status_code"),
                d.get("content_type"),
            )
            for d in self._buffer
        ]
        await self._conn.executemany(
            """
            INSERT OR REPLACE INTO pages
                (url, title, text, links, metadata, crawled_at, status_code, content_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await self._conn.commit()
        self._buffer.clear()

    async def close(self):
        async with self._lock:
            await self._flush()
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
