import pytest
from aiohttp import web

from advanced_crawler import AdvancedCrawler
from config import CrawlerConfig
from data_storage import read_json_lines

SITEMAP = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{page_url}</loc></url>
</urlset>
"""


@pytest.fixture
async def site(aiohttp_server):
    async def open_robots(request):
        return web.Response(text="User-agent: *\n", content_type="text/plain")

    async def page(request):
        return web.Response(
            text='<html><title>Page</title><a href="/other">other</a></html>',
            content_type="text/html",
        )

    async def other(request):
        return web.Response(text="<html><title>Other</title></html>", content_type="text/html")

    async def sitemap(request):
        page_url = str(request.url.origin()) + "/page"
        return web.Response(text=SITEMAP.format(page_url=page_url), content_type="application/xml")

    app = web.Application()
    app.router.add_get("/robots.txt", open_robots)
    app.router.add_get("/page", page)
    app.router.add_get("/other", other)
    app.router.add_get("/sitemap.xml", sitemap)
    return await aiohttp_server(app)


@pytest.mark.asyncio
async def test_crawl_with_explicit_start_urls_populates_stats_and_storage(site, tmp_path):
    output = str(tmp_path / "out.jsonl")
    config = CrawlerConfig(
        start_urls=[str(site.make_url("/page"))],
        max_pages=5,
        max_depth=1,
        requests_per_second=100,
        output=output,
        log_file=None,
    )

    async with AdvancedCrawler(config) as crawler:
        results = await crawler.crawl()
        stats = crawler.get_stats()

    assert len(results) == 2
    assert stats["total_pages"] == 2
    assert stats["successful"] == 2
    assert stats["status_codes"] == {200: 2}

    saved = await read_json_lines(output)
    assert len(saved) == 2


@pytest.mark.asyncio
async def test_crawl_seeded_from_sitemap(site, tmp_path):
    output = str(tmp_path / "out.jsonl")
    config = CrawlerConfig(
        sitemap_urls=[str(site.make_url("/sitemap.xml"))],
        max_pages=1,
        max_depth=0,
        requests_per_second=100,
        output=output,
        log_file=None,
    )

    async with AdvancedCrawler(config) as crawler:
        results = await crawler.crawl()

    assert len(results) == 1


@pytest.mark.asyncio
async def test_crawl_raises_without_any_start_urls(tmp_path):
    config = CrawlerConfig(start_urls=[], sitemap_urls=[], output=str(tmp_path / "out.jsonl"), log_file=None)

    async with AdvancedCrawler(config) as crawler:
        with pytest.raises(ValueError):
            await crawler.crawl()


@pytest.mark.asyncio
async def test_export_to_json_and_html_after_crawl(site, tmp_path):
    config = CrawlerConfig(
        start_urls=[str(site.make_url("/page"))],
        max_pages=5,
        max_depth=0,
        requests_per_second=100,
        output=str(tmp_path / "out.jsonl"),
        log_file=None,
    )

    async with AdvancedCrawler(config) as crawler:
        await crawler.crawl()
        crawler.export_to_json(str(tmp_path / "stats.json"))
        crawler.export_to_html_report(str(tmp_path / "report.html"))

    assert (tmp_path / "stats.json").exists()
    assert (tmp_path / "report.html").exists()
