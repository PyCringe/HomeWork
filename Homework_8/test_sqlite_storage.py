import json

import aiosqlite
import pytest

from sqlite_storage import SQLiteStorage

RECORD = {
    "url": "https://a.com",
    "title": "A",
    "text": "hello",
    "links": ["https://a.com/x"],
    "metadata": {"k": "v"},
    "crawled_at": "2026-01-01T00:00:00+00:00",
    "status_code": 200,
    "content_type": "text/html",
}


@pytest.mark.asyncio
async def test_init_db_creates_table_and_indexes(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = SQLiteStorage(db_path)
    await storage.init_db()

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pages'")
        assert await cursor.fetchone() is not None

        cursor = await conn.execute("PRAGMA index_list(pages)")
        indexes = [row[1] for row in await cursor.fetchall()]
        assert any("status" in name for name in indexes)

    await storage.close()


@pytest.mark.asyncio
async def test_save_below_batch_size_is_buffered_not_flushed(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = SQLiteStorage(db_path, batch_size=5)
    await storage.save(RECORD)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM pages")
        count = (await cursor.fetchone())[0]
    assert count == 0  # still buffered, not flushed

    await storage.close()


@pytest.mark.asyncio
async def test_save_flushes_at_batch_size(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = SQLiteStorage(db_path, batch_size=2)
    await storage.save({**RECORD, "url": "https://a.com/1"})
    await storage.save({**RECORD, "url": "https://a.com/2"})

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM pages")
        count = (await cursor.fetchone())[0]
    assert count == 2

    await storage.close()


@pytest.mark.asyncio
async def test_close_flushes_remaining_buffer(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = SQLiteStorage(db_path, batch_size=10)
    await storage.save(RECORD)
    await storage.close()

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT url, title, links, metadata FROM pages")
        row = await cursor.fetchone()

    assert row[0] == "https://a.com"
    assert row[1] == "A"
    assert json.loads(row[2]) == ["https://a.com/x"]
    assert json.loads(row[3]) == {"k": "v"}


@pytest.mark.asyncio
async def test_save_replaces_existing_url(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = SQLiteStorage(db_path, batch_size=1)
    await storage.save(RECORD)
    await storage.save({**RECORD, "title": "Updated"})
    await storage.close()

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT COUNT(*), title FROM pages WHERE url = ?", (RECORD["url"],))
        count, title = await cursor.fetchone()

    assert count == 1
    assert title == "Updated"
