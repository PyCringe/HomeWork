import asyncio
import contextlib
import logging
import time

from config import CrawlerConfig
from crawler import AsyncCrawler
from crawler_stats import CrawlerStats
from csv_storage import CSVStorage
from data_storage import DataStorage, JSONStorage
from logging_setup import setup_logging
from sitemap_parser import SitemapParser
from sqlite_storage import SQLiteStorage

logger = logging.getLogger("advanced_crawler")


class AdvancedCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        setup_logging(config.log_file, config.log_level)

        self.stats = CrawlerStats()
        self.storage = _build_storage(config)
        self.crawler = AsyncCrawler(
            max_concurrent=config.max_concurrent,
            max_depth=config.max_depth,
            requests_per_second=config.requests_per_second,
            respect_robots=config.respect_robots,
            user_agent=config.user_agent,
            storage=self.storage,
        )
        self.sitemap_parser = SitemapParser()

    @classmethod
    def from_config(cls, path: str) -> "AdvancedCrawler":
        return cls(CrawlerConfig.from_file(path))

    async def _resolve_start_urls(self) -> list[str]:
        urls = list(self.config.start_urls)
        for sitemap_url in self.config.sitemap_urls:
            found = await self.sitemap_parser.fetch_sitemap(sitemap_url)
            logger.info("sitemap %s contributed %d URLs", sitemap_url, len(found))
            urls.extend(found)

        seen = set()
        deduped = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                deduped.append(url)
        return deduped

    async def _progress_monitor(self, interval: float = 0.5):
        start = time.monotonic()
        try:
            while True:
                await asyncio.sleep(interval)
                done = len(self.crawler.visited_urls)
                elapsed = time.monotonic() - start
                rate = done / elapsed if elapsed > 0 else 0.0
                max_pages = self.config.max_pages
                pct = min(done / max_pages * 100, 100.0) if max_pages else 0.0
                remaining = max(max_pages - done, 0)
                eta = remaining / rate if rate > 0 else None

                bar_len = 30
                filled = int(bar_len * pct / 100)
                bar = "#" * filled + "-" * (bar_len - filled)
                eta_str = f"{eta:.0f}s" if eta is not None else "?"
                print(
                    f"\r[{bar}] {pct:5.1f}% ({done}/{max_pages}) {rate:.2f} pages/s ETA {eta_str}  ",
                    end="", flush=True,
                )
        except asyncio.CancelledError:
            pass

    async def crawl(self) -> dict:
        start_urls = await self._resolve_start_urls()
        if not start_urls:
            raise ValueError("no start URLs resolved from config.start_urls or config.sitemap_urls")

        self.stats.start()
        monitor = asyncio.create_task(self._progress_monitor())
        try:
            results = await self.crawler.crawl(
                start_urls,
                max_pages=self.config.max_pages,
                same_domain_only=self.config.same_domain_only,
                exclude_patterns=self.config.exclude_patterns or None,
                include_patterns=self.config.include_patterns or None,
            )
        finally:
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
            print()
        self.stats.stop()

        for url, record in results.items():
            self.stats.record_success(url, record.get("status_code", 0))
        for url in self.crawler.failed_urls:
            self.stats.record_failure(url)

        return results

    def get_stats(self) -> dict:
        return self.stats.summary()

    def export_to_json(self, filename: str):
        self.stats.export_to_json(filename)

    def export_to_html_report(self, filename: str):
        self.stats.export_to_html_report(filename)

    async def close(self):
        await self.crawler.close()
        await self.sitemap_parser.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()


def _build_storage(config: CrawlerConfig) -> DataStorage | None:
    if not config.output:
        return None
    if config.output_format == "csv":
        return CSVStorage(config.output)
    if config.output_format == "sqlite":
        return SQLiteStorage(config.output)
    if config.output_format == "json_array":
        return JSONStorage(config.output, mode="array")
    return JSONStorage(config.output, mode="lines")
