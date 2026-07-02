import pytest
from aiohttp import web

from crawler import AsyncCrawler
from data_storage import DataStorage, JSONStorage, read_json_lines


class FailingStorage(DataStorage):
    def __init__(self):
        self.saved = []

    async def save(self, data: dict):
        raise RuntimeError("disk full")

    async def close(self):
        pass


@pytest.fixture
async def page_server(aiohttp_server):
    async def page(request):
        return web.Response(text="<html><title>Saved page</title></html>", content_type="text/html")

    app = web.Application()
    app.router.add_get("/page", page)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_fetch_and_parse_saves_to_storage(page_server, tmp_path):
    path = str(tmp_path / "out.jsonl")
    storage = JSONStorage(path)

    async with AsyncCrawler(respect_robots=False, requests_per_second=100, storage=storage) as crawler:
        await crawler.fetch_and_parse(str(page_server.make_url("/page")))

    records = await read_json_lines(path)
    assert len(records) == 1
    assert records[0]["title"] == "Saved page"
    assert records[0]["status_code"] == 200
    assert "crawled_at" in records[0]


@pytest.mark.asyncio
async def test_storage_failure_does_not_crash_crawl(page_server):
    storage = FailingStorage()

    async with AsyncCrawler(
        respect_robots=False, requests_per_second=100,
        storage=storage, storage_max_retries=1, storage_retry_delay=0.01,
    ) as crawler:
        result = await crawler.fetch_and_parse(str(page_server.make_url("/page")))

    assert result["title"] == "Saved page"
    assert len(crawler.storage_errors) == 1


@pytest.mark.asyncio
async def test_crawl_continues_saving_across_multiple_pages(page_server, tmp_path):
    path = str(tmp_path / "out.jsonl")
    storage = JSONStorage(path)

    async with AsyncCrawler(respect_robots=False, requests_per_second=100, storage=storage, max_depth=0) as crawler:
        await crawler.crawl([str(page_server.make_url("/page"))], max_pages=1)

    records = await read_json_lines(path)
    assert len(records) == 1
