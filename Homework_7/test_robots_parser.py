import pytest
from aiohttp import web

from robots_parser import RobotsParser

ROBOTS_TXT = """
User-agent: *
Disallow: /private
Crawl-delay: 2

User-agent: GoodBot
Disallow:
"""


@pytest.fixture
async def robots_server(aiohttp_server):
    async def robots_handler(request):
        return web.Response(text=ROBOTS_TXT, content_type="text/plain")

    app = web.Application()
    app.router.add_get("/robots.txt", robots_handler)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_fetch_robots_caches_domain(robots_server):
    parser = RobotsParser()
    base_url = str(robots_server.make_url("/"))
    domain = base_url.split("//")[1].rstrip("/")

    assert not parser.has_domain(domain)
    info = await parser.fetch_robots(base_url)
    assert info["fetched"] is True
    assert parser.has_domain(domain)
    await parser.close()


@pytest.mark.asyncio
async def test_can_fetch_respects_disallow(robots_server):
    parser = RobotsParser()
    base_url = str(robots_server.make_url("/"))
    await parser.fetch_robots(base_url)

    allowed_url = str(robots_server.make_url("/public/page"))
    disallowed_url = str(robots_server.make_url("/private/page"))

    assert parser.can_fetch(allowed_url, "*") is True
    assert parser.can_fetch(disallowed_url, "*") is False
    await parser.close()


@pytest.mark.asyncio
async def test_can_fetch_respects_user_agent_specific_rules(robots_server):
    parser = RobotsParser()
    base_url = str(robots_server.make_url("/"))
    await parser.fetch_robots(base_url)

    disallowed_url = str(robots_server.make_url("/private/page"))
    assert parser.can_fetch(disallowed_url, "GoodBot") is True
    await parser.close()


@pytest.mark.asyncio
async def test_get_crawl_delay_reads_directive(robots_server):
    parser = RobotsParser()
    base_url = str(robots_server.make_url("/"))
    domain = base_url.split("//")[1].rstrip("/")
    await parser.fetch_robots(base_url)

    assert parser.get_crawl_delay("*", domain) == 2.0
    await parser.close()


@pytest.mark.asyncio
async def test_can_fetch_defaults_to_allowed_when_uncached():
    parser = RobotsParser()
    assert parser.can_fetch("https://unknown.test/page", "*") is True


@pytest.mark.asyncio
async def test_missing_robots_txt_allows_everything(aiohttp_server):
    app = web.Application()  # no /robots.txt route -> 404
    server = await aiohttp_server(app)
    parser = RobotsParser()
    base_url = str(server.make_url("/"))
    info = await parser.fetch_robots(base_url)

    assert info["fetched"] is False
    assert parser.can_fetch(str(server.make_url("/anything")), "*") is True
    await parser.close()
