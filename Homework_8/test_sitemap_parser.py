import asyncio

import pytest
from aiohttp import web

from sitemap_parser import SitemapParser

FLAT_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://a.com/1</loc></url>
  <url><loc>https://a.com/2</loc></url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>{child_a}</loc></sitemap>
  <sitemap><loc>{child_b}</loc></sitemap>
</sitemapindex>
"""

CHILD_A = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://a.com/x</loc></url>
</urlset>
"""

CHILD_B = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://a.com/y</loc></url>
</urlset>
"""

XXE_SITEMAP = """<?xml version="1.0"?>
<!DOCTYPE urlset [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<urlset><url><loc>&xxe;</loc></url></urlset>
"""


@pytest.mark.asyncio
async def test_fetch_flat_sitemap(aiohttp_server):
    async def sitemap(request):
        return web.Response(text=FLAT_SITEMAP, content_type="application/xml")

    app = web.Application()
    app.router.add_get("/sitemap.xml", sitemap)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/sitemap.xml")))
    await parser.close()

    assert urls == ["https://a.com/1", "https://a.com/2"]


@pytest.mark.asyncio
async def test_fetch_sitemap_index_recurses_into_children(aiohttp_server):
    async def child_a(request):
        return web.Response(text=CHILD_A, content_type="application/xml")

    async def child_b(request):
        return web.Response(text=CHILD_B, content_type="application/xml")

    async def index(request):
        origin = str(request.url.origin())
        return web.Response(
            text=SITEMAP_INDEX.format(child_a=f"{origin}/child_a.xml", child_b=f"{origin}/child_b.xml"),
            content_type="application/xml",
        )

    app = web.Application()
    app.router.add_get("/child_a.xml", child_a)
    app.router.add_get("/child_b.xml", child_b)
    app.router.add_get("/sitemap_index.xml", index)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/sitemap_index.xml")))
    await parser.close()

    assert sorted(urls) == ["https://a.com/x", "https://a.com/y"]


@pytest.mark.asyncio
async def test_malformed_xml_returns_empty_list(aiohttp_server):
    async def broken(request):
        return web.Response(text="<urlset><url><loc>unterminated", content_type="application/xml")

    app = web.Application()
    app.router.add_get("/sitemap.xml", broken)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/sitemap.xml")))
    await parser.close()

    assert urls == []


@pytest.mark.asyncio
async def test_missing_sitemap_returns_empty_list(aiohttp_server):
    app = web.Application()
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/does-not-exist.xml")))
    await parser.close()

    assert urls == []


@pytest.mark.asyncio
async def test_xxe_payload_is_rejected(aiohttp_server):
    async def malicious(request):
        return web.Response(text=XXE_SITEMAP, content_type="application/xml")

    app = web.Application()
    app.router.add_get("/sitemap.xml", malicious)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/sitemap.xml")))
    await parser.close()

    assert urls == []


@pytest.mark.asyncio
async def test_redirect_is_not_followed(aiohttp_server):
    async def target(request):
        return web.Response(text=FLAT_SITEMAP, content_type="application/xml")

    async def redirecting(request):
        raise web.HTTPFound(location=f"{request.url.origin()}/target.xml")

    app = web.Application()
    app.router.add_get("/target.xml", target)
    app.router.add_get("/sitemap.xml", redirecting)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await parser.fetch_sitemap(str(server.make_url("/sitemap.xml")))
    await parser.close()

    assert urls == []


@pytest.mark.asyncio
async def test_self_referencing_index_does_not_infinite_loop(aiohttp_server):
    async def index(request):
        self_url = str(request.url)
        return web.Response(
            text=SITEMAP_INDEX.format(child_a=self_url, child_b=self_url),
            content_type="application/xml",
        )

    app = web.Application()
    app.router.add_get("/loop.xml", index)
    server = await aiohttp_server(app)

    parser = SitemapParser()
    urls = await asyncio.wait_for(parser.fetch_sitemap(str(server.make_url("/loop.xml"))), timeout=5)
    await parser.close()

    assert urls == []
