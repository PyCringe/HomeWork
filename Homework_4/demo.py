import asyncio
import sys

from crawler import AsyncCrawler

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    async with AsyncCrawler(max_concurrent=5, max_depth=2, per_domain_limit=3) as crawler:
        results = await crawler.crawl(
            start_urls=["https://docs.python.org/3/"],
            max_pages=15,
            same_domain_only=True,
            exclude_patterns=[r"\.pdf$", r"/genindex"],
        )

    print(f"\nОбработано: {len(results)} страниц")
    print(f"Ошибок: {len(crawler.failed_urls)}")
    print(f"Всего посещено URL: {len(crawler.visited_urls)}")

    for url, data in list(results.items())[:5]:
        print(f"  {url}")
        print(f"    title: {data['title']}")
        print(f"    links: {len(data['links'])}")

    if crawler.failed_urls:
        print("\nОшибки:")
        for url, error in crawler.failed_urls.items():
            print(f"  {url}: {error}")


if __name__ == "__main__":
    asyncio.run(main())
