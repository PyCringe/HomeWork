import asyncio
import sys

from crawler import AsyncCrawler, RobotsDisallowedError

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    async with AsyncCrawler(
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.3,
        jitter=0.1,
        user_agent="AsyncCrawlerCourseBot/1.0",
        max_depth=1,
    ) as crawler:
        results = await crawler.crawl(
            start_urls=["https://docs.python.org/3/"],
            max_pages=8,
            same_domain_only=True,
        )

        try:
            await crawler.fetch_url("https://docs.python.org/dev/whatsnew/3.15.html")
        except RobotsDisallowedError as e:
            print(f"заблокировано robots.txt: {e}")

    stats = crawler.get_rate_stats()
    print(f"\nОбработано: {len(results)} страниц")
    print(f"Ошибок: {len(crawler.failed_urls)}")
    print(f"Заблокировано robots.txt: {stats['blocked_count']}")
    print(f"Средняя скорость: {stats['current_rate']:.2f} req/s")
    print(f"Средняя задержка между запросами: {stats['average_delay']:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
