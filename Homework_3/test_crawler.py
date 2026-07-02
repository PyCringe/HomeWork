import asyncio

import aiohttp
import pytest
from aiohttp import web

from crawler import AsyncCrawler

PAGE_HTML = """
<html>
<head><title>Fixture Page</title></head>
<body>
    <h1>Hello</h1>
    <a href="/other">Other page</a>
</body>
</html>
"""


@pytest.fixture
async def test_server(aiohttp_server):
    async def page_handler(request):
        return web.Response(text=PAGE_HTML, content_type="text/html")

    async def not_found_handler(request):
        return web.Response(status=404)

    async def slow_handler(request):
        await asyncio.sleep(2)
        return web.Response(text="slow")

    app = web.Application()
    app.router.add_get("/page", page_handler)
    app.router.add_get("/404", not_found_handler)
    app.router.add_get("/slow", slow_handler)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_fetch_url_success(test_server):
    async with AsyncCrawler() as crawler:
        text = await crawler.fetch_url(str(test_server.make_url("/page")))
    assert "Fixture Page" in text


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
async def test_fetch_and_parse_returns_structured_data(test_server):
    url = str(test_server.make_url("/page"))
    async with AsyncCrawler() as crawler:
        result = await crawler.fetch_and_parse(url)

    assert result["url"] == url
    assert result["title"] == "Fixture Page"
    assert result["headings"]["h1"] == ["Hello"]
    assert any(link.endswith("/other") for link in result["links"])
