import asyncio
import sys

from advanced_crawler import AdvancedCrawler
from config import CrawlerConfig

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    config = CrawlerConfig(
        start_urls=["https://docs.python.org/3/"],
        max_pages=10,
        max_depth=1,
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        same_domain_only=True,
        output="results.jsonl",
        log_file="crawler.log",
    )

    async with AdvancedCrawler(config) as crawler:
        await crawler.crawl()

        stats = crawler.get_stats()
        print(f"Обработано: {stats['total_pages']} страниц")
        print(f"Успешно: {stats['successful']}")
        print(f"Ошибок: {stats['failed']}")
        print(f"Скорость: {stats['pages_per_second']:.2f} стр/сек")
        print(f"Статус-коды: {stats['status_codes']}")
        print(f"Топ доменов: {stats['top_domains']}")

        crawler.export_to_json("stats.json")
        crawler.export_to_html_report("report.html")
        print("\nСохранено: stats.json, report.html, results.jsonl, crawler.log")


if __name__ == "__main__":
    asyncio.run(main())
