import pytest
from aiohttp import web

from crawler import AsyncCrawler
from csv_storage import CSVStorage
from errors import TransientError
from robots_parser import RobotsParser


@pytest.fixture
async def redirect_target_server(aiohttp_server):
    """Serves a page at /page and disallows it via robots.txt -- simulates the
    domain a malicious/misconfigured redirect could point to."""
    async def robots(request):
        return web.Response(text="User-agent: *\nDisallow: /page\n", content_type="text/plain")

    async def page(request):
        return web.Response(text="<html><title>should not be fetched</title></html>", content_type="text/html")

    app = web.Application()
    app.router.add_get("/robots.txt", robots)
    app.router.add_get("/page", page)
    return await aiohttp_server(app)


@pytest.fixture
async def redirect_source_server(aiohttp_server, redirect_target_server):
    target_url = str(redirect_target_server.make_url("/page"))

    async def open_robots(request):
        return web.Response(text="User-agent: *\n", content_type="text/plain")

    async def start(request):
        raise web.HTTPFound(location=target_url)

    app = web.Application()
    app.router.add_get("/robots.txt", open_robots)
    app.router.add_get("/start", start)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_redirect_to_disallowed_domain_is_blocked(redirect_source_server):
    async with AsyncCrawler(respect_robots=True, requests_per_second=100) as crawler:
        with pytest.raises(Exception) as exc_info:
            await crawler.fetch_url(str(redirect_source_server.make_url("/start")))

    assert exc_info.type.__name__ == "RobotsDisallowedError"


@pytest.mark.asyncio
async def test_final_url_reflects_redirect_target(redirect_source_server, redirect_target_server):
    async with AsyncCrawler(respect_robots=False, requests_per_second=100) as crawler:
        result = await crawler.fetch_and_parse(str(redirect_source_server.make_url("/start")))

    assert result["requested_url"] == str(redirect_source_server.make_url("/start"))
    assert result["url"] == str(redirect_target_server.make_url("/page"))
    assert result["title"] == "should not be fetched"


@pytest.mark.asyncio
async def test_too_many_redirects_raises_transient_error(aiohttp_server):
    async def bouncing(request):
        raise web.HTTPFound(location=str(request.url))

    app = web.Application()
    app.router.add_get("/loop", bouncing)
    server = await aiohttp_server(app)

    async with AsyncCrawler(respect_robots=False, requests_per_second=100) as crawler:
        with pytest.raises(TransientError):
            await crawler.fetch_url(str(server.make_url("/loop")))


@pytest.mark.asyncio
async def test_robots_txt_redirect_is_treated_as_missing(aiohttp_server, redirect_target_server):
    strict_robots_url = str(redirect_target_server.make_url("/robots.txt"))

    async def robots_redirect(request):
        raise web.HTTPFound(location=strict_robots_url)

    app = web.Application()
    app.router.add_get("/robots.txt", robots_redirect)
    server = await aiohttp_server(app)

    parser = RobotsParser()
    info = await parser.fetch_robots(str(server.make_url("/")))

    assert info["fetched"] is False
    # the redirect to another origin's robots.txt was not followed, so this domain's
    # cached policy falls back to "allow everything" instead of inheriting a foreign policy
    assert parser.can_fetch(str(server.make_url("/anything")), "*") is True
    await parser.close()


@pytest.mark.asyncio
async def test_csv_storage_neutralizes_formula_prefixed_title(tmp_path):
    path = str(tmp_path / "out.csv")
    storage = CSVStorage(path)
    await storage.save({
        "url": "https://a.com",
        "title": "=cmd|'/c calc'!A1",
        "text": "+SUM(1,1)",
        "links": [],
        "metadata": {},
        "crawled_at": "",
        "status_code": 200,
        "content_type": "text/html",
    })

    import csv
    with open(path, encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))

    assert row["title"].startswith("'=")
    assert row["text"].startswith("'+")


@pytest.mark.asyncio
async def test_csv_storage_leaves_normal_values_untouched(tmp_path):
    path = str(tmp_path / "out.csv")
    storage = CSVStorage(path)
    await storage.save({
        "url": "https://a.com",
        "title": "Normal Title",
        "text": "normal text",
        "links": [],
        "metadata": {},
        "crawled_at": "",
        "status_code": 200,
        "content_type": "text/html",
    })

    import csv
    with open(path, encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))

    assert row["title"] == "Normal Title"
    assert row["text"] == "normal text"
