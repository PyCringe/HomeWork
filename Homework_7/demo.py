import asyncio
import sys

from crawler import AsyncCrawler
from csv_storage import CSVStorage
from data_storage import DataStorage, JSONStorage, read_json_lines
from sqlite_storage import SQLiteStorage

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


class MultiStorage(DataStorage):
    """Fans out each save() call to several DataStorage backends at once."""

    def __init__(self, *storages):
        self.storages = storages

    async def save(self, data: dict):
        await asyncio.gather(*(s.save(data) for s in self.storages))

    async def close(self):
        await asyncio.gather(*(s.close() for s in self.storages))


async def main():
    json_storage = JSONStorage("results.jsonl")
    csv_storage = CSVStorage("results.csv")
    db_storage = SQLiteStorage("crawler.db", batch_size=3)
    storage = MultiStorage(json_storage, csv_storage, db_storage)

    async with AsyncCrawler(
        max_concurrent=5,
        max_depth=1,
        requests_per_second=3.0,
        respect_robots=True,
        storage=storage,
    ) as crawler:
        results = await crawler.crawl(
            start_urls=["https://docs.python.org/3/"],
            max_pages=6,
            same_domain_only=True,
        )

    print(f"Обработано: {len(results)} страниц")
    print(f"Ошибок сохранения: {len(crawler.storage_errors)}")

    saved = await read_json_lines("results.jsonl")
    print(f"\nЗаписей в results.jsonl: {len(saved)}")
    for record in saved[:3]:
        print(f"  {record['url']} — {record['title']}")

    import aiosqlite
    async with aiosqlite.connect("crawler.db") as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM pages")
        count = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT url, status_code FROM pages LIMIT 3")
        rows = await cursor.fetchall()
    print(f"\nЗаписей в crawler.db: {count}")
    for url, status in rows:
        print(f"  {url} — status {status}")

    with open("results.csv", encoding="utf-8") as f:
        line_count = sum(1 for _ in f) - 1  # minus header
    print(f"\nСтрок в results.csv (без заголовка): {line_count}")


if __name__ == "__main__":
    asyncio.run(main())
