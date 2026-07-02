import pytest
from aiohttp import web

from cli import async_main, build_arg_parser, build_config


def test_build_config_applies_cli_overrides():
    parser = build_arg_parser()
    args = parser.parse_args([
        "--urls", "https://a.com", "https://b.com",
        "--max-pages", "7",
        "--rate-limit", "2.5",
        "--no-respect-robots",
    ])
    config = build_config(args)

    assert config.start_urls == ["https://a.com", "https://b.com"]
    assert config.max_pages == 7
    assert config.requests_per_second == 2.5
    assert config.respect_robots is False


@pytest.mark.asyncio
async def test_async_main_requires_urls_or_config():
    with pytest.raises(SystemExit):
        await async_main([])


@pytest.mark.asyncio
async def test_async_main_runs_end_to_end(aiohttp_server, tmp_path, capsys):
    async def open_robots(request):
        return web.Response(text="User-agent: *\n", content_type="text/plain")

    async def page(request):
        return web.Response(text="<html><title>CLI page</title></html>", content_type="text/html")

    app = web.Application()
    app.router.add_get("/robots.txt", open_robots)
    app.router.add_get("/page", page)
    server = await aiohttp_server(app)

    output = str(tmp_path / "out.jsonl")
    report = str(tmp_path / "report.html")

    results = await async_main([
        "--urls", str(server.make_url("/page")),
        "--max-pages", "1",
        "--max-depth", "0",
        "--rate-limit", "100",
        "--output", output,
        "--report", report,
        "--log-file", "",
    ])

    assert len(results) == 1
    captured = capsys.readouterr()
    assert "Обработано: 1" in captured.out
    assert (tmp_path / "report.html").exists()
