import asyncio

import pytest
from aiohttp import web

from crawler import AsyncCrawler
from errors import PermanentError, TransientError
from retry_strategy import RetryStrategy


@pytest.fixture
async def flaky_server(aiohttp_server):
    state = {"attempts_503": 0, "attempts_timeout": 0}

    async def eventually_ok(request):
        state["attempts_503"] += 1
        if state["attempts_503"] < 3:
            return web.Response(status=503)
        return web.Response(text="<html><title>ok</title></html>", content_type="text/html")

    async def always_404(request):
        return web.Response(status=404)

    async def always_403(request):
        return web.Response(status=403)

    async def slow(request):
        state["attempts_timeout"] += 1
        await asyncio.sleep(1)
        return web.Response(text="slow")

    app = web.Application()
    app.router.add_get("/eventually-ok", eventually_ok)
    app.router.add_get("/always-404", always_404)
    app.router.add_get("/always-403", always_403)
    app.router.add_get("/slow", slow)
    server = await aiohttp_server(app)
    server.state = state
    return server


@pytest.mark.asyncio
async def test_fetch_url_retries_503_until_success(flaky_server):
    retry_strategy = RetryStrategy(max_retries=5, base_delay=0.01)
    async with AsyncCrawler(respect_robots=False, requests_per_second=100, retry_strategy=retry_strategy) as crawler:
        text = await crawler.fetch_url(str(flaky_server.make_url("/eventually-ok")))
    assert "ok" in text
    assert flaky_server.state["attempts_503"] == 3


@pytest.mark.asyncio
async def test_fetch_url_does_not_retry_404(flaky_server):
    retry_strategy = RetryStrategy(max_retries=5, base_delay=0.01)
    async with AsyncCrawler(respect_robots=False, requests_per_second=100, retry_strategy=retry_strategy) as crawler:
        with pytest.raises(PermanentError):
            await crawler.fetch_url(str(flaky_server.make_url("/always-404")))
    assert crawler.retry_strategy.stats.errors_by_type["PermanentError"] == 1


@pytest.mark.asyncio
async def test_fetch_url_does_not_retry_403(flaky_server):
    retry_strategy = RetryStrategy(max_retries=5, base_delay=0.01)
    async with AsyncCrawler(respect_robots=False, requests_per_second=100, retry_strategy=retry_strategy) as crawler:
        with pytest.raises(PermanentError):
            await crawler.fetch_url(str(flaky_server.make_url("/always-403")))


@pytest.mark.asyncio
async def test_fetch_url_retries_on_timeout(flaky_server):
    retry_strategy = RetryStrategy(max_retries=2, base_delay=0.01)
    async with AsyncCrawler(
        respect_robots=False, requests_per_second=100,
        read_timeout=0.1, retry_strategy=retry_strategy,
    ) as crawler:
        with pytest.raises(TransientError):
            await crawler.fetch_url(str(flaky_server.make_url("/slow")))
    assert flaky_server.state["attempts_timeout"] == 3


@pytest.mark.asyncio
async def test_crawl_records_permanent_failures_without_crashing(flaky_server):
    async with AsyncCrawler(respect_robots=False, requests_per_second=100, max_depth=0) as crawler:
        results = await crawler.crawl(
            [str(flaky_server.make_url("/always-404"))],
            max_pages=1,
        )
    assert results == {}
    assert len(crawler.failed_urls) == 1


@pytest.mark.asyncio
async def test_get_error_stats_reports_summary(flaky_server):
    retry_strategy = RetryStrategy(max_retries=5, base_delay=0.01)
    async with AsyncCrawler(respect_robots=False, requests_per_second=100, retry_strategy=retry_strategy) as crawler:
        await crawler.fetch_url(str(flaky_server.make_url("/eventually-ok")))
        stats = crawler.get_error_stats()

    assert stats["successful_retries"] == 1
    assert stats["errors_by_type"]["TransientError"] == 2
