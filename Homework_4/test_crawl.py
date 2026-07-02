import pytest
from aiohttp import web

from crawler import AsyncCrawler


def page(title: str, links: list[str]) -> str:
    anchors = "".join(f'<a href="{link}">{link}</a>' for link in links)
    return f"<html><head><title>{title}</title></head><body>{anchors}</body></html>"


@pytest.fixture
async def hub_site(aiohttp_server):
    async def hub(request):
        leaves = [f"/leaf{i}" for i in range(20)]
        return web.Response(text=page("hub", leaves), content_type="text/html")

    async def leaf(request):
        return web.Response(text=page(request.path.strip("/"), []), content_type="text/html")

    app = web.Application()
    app.router.add_get("/", hub)
    for i in range(20):
        app.router.add_get(f"/leaf{i}", leaf)
    return await aiohttp_server(app)


@pytest.fixture
async def site(aiohttp_server):
    async def root(request):
        return web.Response(text=page("root", ["/a", "/b", "http://external.test/x"]), content_type="text/html")

    async def page_a(request):
        return web.Response(text=page("a", ["/c"]), content_type="text/html")

    async def page_b(request):
        return web.Response(text=page("b", ["/a", "/d"]), content_type="text/html")

    async def page_c(request):
        return web.Response(text=page("c", []), content_type="text/html")

    async def page_d(request):
        return web.Response(text=page("d", []), content_type="text/html")

    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/a", page_a)
    app.router.add_get("/b", page_b)
    app.router.add_get("/c", page_c)
    app.router.add_get("/d", page_d)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_crawl_respects_max_depth(site):
    root_url = str(site.make_url("/"))
    async with AsyncCrawler(max_concurrent=5, max_depth=1) as crawler:
        results = await crawler.crawl([root_url], max_pages=50)

    titles = {r["title"] for r in results.values()}
    assert titles == {"root", "a", "b"}


@pytest.mark.asyncio
async def test_crawl_does_not_revisit_urls(site):
    root_url = str(site.make_url("/"))
    async with AsyncCrawler(max_concurrent=5, max_depth=2) as crawler:
        results = await crawler.crawl([root_url], max_pages=50)

    assert len(crawler.visited_urls) == len(set(crawler.visited_urls))
    urls_seen = list(results.keys())
    assert len(urls_seen) == len(set(urls_seen))


@pytest.mark.asyncio
async def test_crawl_filters_same_domain_only(site):
    root_url = str(site.make_url("/"))
    async with AsyncCrawler(max_concurrent=5, max_depth=1) as crawler:
        await crawler.crawl([root_url], max_pages=50, same_domain_only=True)

    assert not any("external.test" in url for url in crawler.visited_urls)


@pytest.mark.asyncio
async def test_crawl_exclude_patterns(site):
    root_url = str(site.make_url("/"))
    async with AsyncCrawler(max_concurrent=5, max_depth=2) as crawler:
        results = await crawler.crawl([root_url], max_pages=50, exclude_patterns=[r"/b$"])

    titles = {r["title"] for r in results.values()}
    assert "b" not in titles
    assert "d" not in titles


@pytest.mark.asyncio
async def test_crawl_respects_max_pages(site):
    root_url = str(site.make_url("/"))
    async with AsyncCrawler(max_concurrent=1, max_depth=2) as crawler:
        results = await crawler.crawl([root_url], max_pages=2)

    assert len(results) <= 2


@pytest.mark.asyncio
async def test_crawl_does_not_overshoot_max_pages_under_concurrency(hub_site):
    root_url = str(hub_site.make_url("/"))
    async with AsyncCrawler(max_concurrent=8, max_depth=1, per_domain_limit=8) as crawler:
        await crawler.crawl([root_url], max_pages=5)

    assert len(crawler.visited_urls) == 5
