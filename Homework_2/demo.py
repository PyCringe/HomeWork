import asyncio
import sys
import time

import aiohttp

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from crawler import AsyncCrawler

URLS = [
    "https://httpbin.org/get",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/2",
    "https://httpbin.org/status/404",
    "https://httpbin.org/status/500",
    "https://example.com",
    "https://httpbin.org/uuid",
    "https://this-domain-does-not-exist-12345.invalid",
]


async def run_parallel():
    print("Параллельная загрузка:")
    start = time.perf_counter()
    async with AsyncCrawler(max_concurrent=5) as crawler:
        results = await crawler.fetch_urls(URLS)
    elapsed = time.perf_counter() - start

    ok = sum(1 for r in results.values() if not isinstance(r, Exception))
    for url, result in results.items():
        if isinstance(result, Exception):
            print(f"  fail  {url} -> {type(result).__name__}: {result}")
        else:
            print(f"  ok    {url} -> {len(result)} bytes")
    print(f"{ok}/{len(URLS)} успешно, {elapsed:.2f}s\n")
    return elapsed


async def run_sequential():
    print("Последовательная загрузка (для сравнения):")
    ok = 0
    start = time.perf_counter()
    async with AsyncCrawler(max_concurrent=1) as crawler:
        for url in URLS:
            try:
                text = await crawler.fetch_url(url)
                ok += 1
                print(f"  ok    {url} -> {len(text)} bytes")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"  fail  {url} -> {type(e).__name__}: {e}")
    elapsed = time.perf_counter() - start
    print(f"{ok}/{len(URLS)} успешно, {elapsed:.2f}s\n")
    return elapsed


async def main():
    parallel_time = await run_parallel()
    sequential_time = await run_sequential()

    speedup = sequential_time / parallel_time if parallel_time else 0
    print(f"параллельно {parallel_time:.2f}s vs последовательно {sequential_time:.2f}s, ускорение {speedup:.2f}x")


if __name__ == "__main__":
    asyncio.run(main())
