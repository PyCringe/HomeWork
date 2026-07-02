import asyncio
import logging
import re
import time
from urllib.parse import urlparse

import aiohttp

from crawler_queue import CrawlerQueue
from html_parser import HTMLParser
from rate_limiter import RateLimiter
from robots_parser import RobotsParser
from semaphore_manager import SemaphoreManager

logger = logging.getLogger("async_crawler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class RobotsDisallowedError(Exception):
    pass


class AsyncCrawler:
    def __init__(
        self,
        max_concurrent: int = 10,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        follow_external_links: bool = True,
        max_depth: int = 2,
        per_domain_limit: int = 2,
        requests_per_second: float = 1.0,
        per_domain_rate_limit: bool = True,
        min_delay: float = 0.0,
        jitter: float = 0.0,
        respect_robots: bool = True,
        user_agent: str = "AsyncCrawlerBot/1.0",
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ):
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth
        self.per_domain_limit = per_domain_limit
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = aiohttp.ClientTimeout(
            connect=connect_timeout,
            sock_read=read_timeout,
        )
        self._session: aiohttp.ClientSession | None = None
        self._parser = HTMLParser(follow_external_links=follow_external_links)
        self._rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            per_domain=per_domain_rate_limit,
            min_delay=min_delay,
            jitter=jitter,
        )
        self._robots = RobotsParser() if respect_robots else None

        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}
        self.processed_urls: dict[str, dict] = {}
        self.blocked_urls: set[str] = set()

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=connector,
                headers={"User-Agent": self.user_agent},
            )
        return self._session

    async def fetch_url(self, url: str) -> str:
        session = self._get_session()
        domain = urlparse(url).netloc

        crawl_delay = None
        if self._robots is not None:
            if not self._robots.has_domain(domain):
                await self._robots.fetch_robots(url)
            if not self._robots.can_fetch(url, self.user_agent):
                self.blocked_urls.add(url)
                logger.warning("blocked by robots.txt: %s", url)
                raise RobotsDisallowedError(url)
            crawl_delay = self._robots.get_crawl_delay(self.user_agent, domain)

        for attempt in range(self.max_retries + 1):
            await self._rate_limiter.acquire(domain, min_delay=crawl_delay)
            async with self._semaphore:
                logger.info("-> start fetching %s", url)
                try:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        text = await response.text()
                        logger.info("<- done %s (status=%s, %d bytes)", url, response.status, len(text))
                        return text
                except asyncio.TimeoutError:
                    if attempt >= self.max_retries:
                        logger.warning("timeout fetching %s, giving up", url)
                        raise
                except aiohttp.ClientResponseError as e:
                    if e.status < 500 or attempt >= self.max_retries:
                        logger.warning("HTTP %s on %s: %s", e.status, url, e.message)
                        raise
                except aiohttp.ClientError as e:
                    if attempt >= self.max_retries:
                        logger.warning("network error on %s: %s", url, type(e).__name__)
                        raise

            backoff = self.backoff_base * (2 ** attempt)
            logger.warning("retrying %s in %.2fs (attempt %d/%d)", url, backoff, attempt + 1, self.max_retries)
            await asyncio.sleep(backoff)

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        async def _safe_fetch(url: str):
            try:
                return url, await self.fetch_url(url)
            except (aiohttp.ClientError, asyncio.TimeoutError, RobotsDisallowedError) as e:
                return url, e

        results = await asyncio.gather(*(_safe_fetch(u) for u in urls))
        return dict(results)

    async def fetch_and_parse(self, url: str) -> dict:
        html = await self.fetch_url(url)
        return await self._parser.parse_html(html, url)

    def get_rate_stats(self) -> dict:
        return {
            "current_rate": self._rate_limiter.current_rate,
            "average_delay": self._rate_limiter.average_delay,
            "blocked_count": len(self.blocked_urls),
        }

    def _link_allowed(self, url: str, allowed_domains, exclude_patterns, include_patterns) -> bool:
        if allowed_domains is not None and urlparse(url).netloc not in allowed_domains:
            return False
        if exclude_patterns and any(re.search(p, url) for p in exclude_patterns):
            return False
        if include_patterns and not any(re.search(p, url) for p in include_patterns):
            return False
        return True

    async def crawl(
        self,
        start_urls: list[str],
        max_pages: int = 100,
        same_domain_only: bool = False,
        exclude_patterns: list[str] | None = None,
        include_patterns: list[str] | None = None,
    ) -> dict[str, dict]:
        queue = CrawlerQueue()
        semaphores = SemaphoreManager(
            global_limit=self.max_concurrent,
            per_domain_limit=self.per_domain_limit,
        )
        allowed_domains = {urlparse(u).netloc for u in start_urls} if same_domain_only else None

        for url in start_urls:
            queue.add_url(url, priority=10, depth=0)

        async def worker():
            while True:
                if len(self.visited_urls) >= max_pages:
                    return
                url = await queue.get_next()
                if url is None:
                    if semaphores.active_count == 0:
                        return
                    await asyncio.sleep(0.05)
                    continue
                if url in self.visited_urls:
                    continue
                if len(self.visited_urls) >= max_pages:
                    return
                self.visited_urls.add(url)

                depth = queue.get_depth(url)
                if depth > self.max_depth:
                    continue

                async with semaphores.acquire(url):
                    try:
                        result = await self.fetch_and_parse(url)
                    except RobotsDisallowedError:
                        continue
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        queue.mark_failed(url, str(e))
                        self.failed_urls[url] = str(e)
                        continue

                queue.mark_processed(url)
                self.processed_urls[url] = result

                stats = queue.get_stats()
                rate_stats = self.get_rate_stats()
                logger.info(
                    "processed=%d queued=%d failed=%d blocked=%d rate=%.2f req/s avg_delay=%.2fs",
                    len(self.processed_urls), stats["queued"], len(self.failed_urls),
                    rate_stats["blocked_count"], rate_stats["current_rate"], rate_stats["average_delay"],
                )

                if depth < self.max_depth:
                    for link in result["links"]:
                        if link in self.visited_urls:
                            continue
                        if not self._link_allowed(link, allowed_domains, exclude_patterns, include_patterns):
                            continue
                        queue.add_url(link, depth=depth + 1)

        workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrent)]
        await asyncio.gather(*workers)
        return self.processed_urls

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
        if self._robots is not None:
            await self._robots.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()
