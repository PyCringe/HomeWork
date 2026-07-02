import asyncio

import aiohttp
import pytest
from aiohttp import web

from crawler import AsyncCrawler


@pytest.fixture
async def test_server(aiohttp_server):
    async def ok_handler(request):
        return web.Response(text="hello world")

    async def not_found_handler(request):
        return web.Response(status=404)

    async def slow_handler(request):
        await asyncio.sleep(2)
        return web.Response(text="slow")

    app = web.Application()
    app.router.add_get("/ok", ok_handler)
    app.router.add_get("/404", not_found_handler)
    app.router.add_get("/slow", slow_handler)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_fetch_url_success(test_server):
    async with AsyncCrawler() as crawler:
        text = await crawler.fetch_url(str(test_server.make_url("/ok")))
    assert text == "hello world"


@pytest.mark.asyncio
async def test_fetch_url_404_raises(test_server):
    async with AsyncCrawler() as crawler:
        with pytest.raises(aiohttp.ClientResponseError):
            await crawler.fetch_url(str(test_server.make_url("/404")))


@pytest.mark.asyncio
async def test_fetch_url_timeout(test_server):
    async with AsyncCrawler(read_timeout=0.2) as crawler:
        with pytest.raises(asyncio.TimeoutError):
            await crawler.fetch_url(str(test_server.make_url("/slow")))


@pytest.mark.asyncio
async def test_fetch_urls_mixed_results(test_server):
    urls = [
        str(test_server.make_url("/ok")),
        str(test_server.make_url("/404")),
    ]
    async with AsyncCrawler() as crawler:
        results = await crawler.fetch_urls(urls)

    assert results[urls[0]] == "hello world"
    assert isinstance(results[urls[1]], aiohttp.ClientResponseError)


@pytest.mark.asyncio
async def test_fetch_urls_does_not_raise_on_error(test_server):
    urls = [str(test_server.make_url("/404")) for _ in range(3)]
    async with AsyncCrawler() as crawler:
        results = await crawler.fetch_urls(urls)
    assert len(results) == 1  # same URL repeated -> single dict key
    assert isinstance(next(iter(results.values())), aiohttp.ClientResponseError)


@pytest.mark.asyncio
async def test_close_is_idempotent(test_server):
    crawler = AsyncCrawler()
    await crawler.fetch_url(str(test_server.make_url("/ok")))
    await crawler.close()
    await crawler.close()  # should not raise


@pytest.mark.asyncio
async def test_max_concurrent_limits_parallelism(test_server):
    active = 0
    peak = 0

    async def tracking_handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.2)
        active -= 1
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/track", tracking_handler)
    from aiohttp.test_utils import TestServer

    server = TestServer(app)
    await server.start_server()
    try:
        url = str(server.make_url("/track"))
        async with AsyncCrawler(max_concurrent=2) as crawler:
            await crawler.fetch_urls([url] * 6)
        assert peak <= 2
    finally:
        await server.close()
