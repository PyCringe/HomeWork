import asyncio
import sys

from crawler import AsyncCrawler

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

URLS = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://docs.python.org/3/",
]


async def main():
    async with AsyncCrawler(max_concurrent=3) as crawler:
        results = await asyncio.gather(
            *(crawler.fetch_and_parse(url) for url in URLS),
            return_exceptions=True,
        )

    for url, result in zip(URLS, results):
        if isinstance(result, Exception):
            print(f"{url}: {type(result).__name__}: {result}")
            continue

        print(f"{url}")
        print(f"  title:       {result['title']}")
        print(f"  text_length: {len(result['text'])}")
        print(f"  links_count: {len(result['links'])}")
        print(f"  images:      {len(result['images'])}")
        print(f"  headings h1: {result['headings']['h1'][:3]}")
        for link in result["links"][:5]:
            print(f"    - {link}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
