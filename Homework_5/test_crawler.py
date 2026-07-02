import time

import pytest
from aiohttp import web

from crawler import AsyncCrawler, RobotsDisallowedError

ROBOTS_TXT = """
User-agent: *
Disallow: /secret
"""


@pytest.fixture
async def guarded_server(aiohttp_server):
    async def robots_handler(request):
        return web.Response(text=ROBOTS_TXT, content_type="text/plain")

    async def public_handler(request):
        return web.Response(text="<html><title>public</title></html>", content_type="text/html")

    async def secret_handler(request):
        return web.Response(text="<html><title>secret</title></html>", content_type="text/html")

    async def root_handler(request):
        return web.Response(
            text='<html><a href="/public">public</a><a href="/secret">secret</a></html>',
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/robots.txt", robots_handler)
    app.router.add_get("/public", public_handler)
    app.router.add_get("/secret", secret_handler)
    app.router.add_get("/", root_handler)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_fetch_url_raises_on_disallowed_path(guarded_server):
    async with AsyncCrawler(respect_robots=True, requests_per_second=100) as crawler:
        with pytest.raises(RobotsDisallowedError):
            await crawler.fetch_url(str(guarded_server.make_url("/secret")))
    assert str(guarded_server.make_url("/secret")) in crawler.blocked_urls


@pytest.mark.asyncio
async def test_fetch_url_allows_public_path(guarded_server):
    async with AsyncCrawler(respect_robots=True, requests_per_second=100) as crawler:
        text = await crawler.fetch_url(str(guarded_server.make_url("/public")))
    assert "public" in text


@pytest.mark.asyncio
async def test_respect_robots_false_ignores_disallow(guarded_server):
    async with AsyncCrawler(respect_robots=False, requests_per_second=100) as crawler:
        text = await crawler.fetch_url(str(guarded_server.make_url("/secret")))
    assert "secret" in text


@pytest.mark.asyncio
async def test_rate_limiting_delays_sequential_requests(guarded_server):
    async with AsyncCrawler(respect_robots=False, requests_per_second=5, max_concurrent=1) as crawler:
        start = time.monotonic()
        await crawler.fetch_url(str(guarded_server.make_url("/public")))
        await crawler.fetch_url(str(guarded_server.make_url("/public")))
        elapsed = time.monotonic() - start
    assert elapsed >= 0.2 - 0.05


@pytest.mark.asyncio
async def test_get_rate_stats_reports_blocked_count(guarded_server):
    async with AsyncCrawler(respect_robots=True, requests_per_second=100) as crawler:
        with pytest.raises(RobotsDisallowedError):
            await crawler.fetch_url(str(guarded_server.make_url("/secret")))
        stats = crawler.get_rate_stats()
    assert stats["blocked_count"] == 1


@pytest.mark.asyncio
async def test_crawl_skips_robots_disallowed_links(guarded_server):
    async with AsyncCrawler(respect_robots=True, requests_per_second=100, max_depth=1) as crawler:
        results = await crawler.crawl([str(guarded_server.make_url("/"))], max_pages=10)

    titles = {r["title"] for r in results.values()}
    assert "public" in titles
    assert "secret" not in titles
