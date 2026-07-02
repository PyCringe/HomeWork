import asyncio
import json
import sys

from aiohttp import web

from crawler import AsyncCrawler
from errors import PermanentError
from retry_strategy import RetryStrategy

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


async def start_flaky_server():
    state = {"attempts": 0}

    async def eventually_ok(request):
        state["attempts"] += 1
        if state["attempts"] < 3:
            return web.Response(status=503)
        return web.Response(text="<html><title>Recovered page</title></html>", content_type="text/html")

    async def gone(request):
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/flaky", eventually_ok)
    app.router.add_get("/gone", gone)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8765)
    await site.start()
    return runner, "http://127.0.0.1:8765"


async def main():
    runner, base_url = await start_flaky_server()

    retry_strategy = RetryStrategy(max_retries=4, base_delay=0.2, backoff_factor=2.0)
    async with AsyncCrawler(
        respect_robots=False,
        requests_per_second=100,
        retry_strategy=retry_strategy,
    ) as crawler:
        print("Запрос к /flaky (отвечает 503 дважды, затем 200):")
        text = await crawler.fetch_url(f"{base_url}/flaky")
        print(f"  успех после повторов: {text[:40]}...")

        print("\nЗапрос к /gone (постоянная ошибка 404, повторов быть не должно):")
        try:
            await crawler.fetch_url(f"{base_url}/gone")
        except PermanentError as e:
            print(f"  не повторяли, сразу отказ: {e}")

        stats = crawler.get_error_stats()
        print("\nСтатистика ошибок:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    await runner.cleanup()

    report_path = "error_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\nОтчёт сохранён в {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
