import asyncio
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import aiohttp

from circuit_breaker import CircuitBreaker
from crawler_queue import CrawlerQueue
from data_storage import DataStorage
from errors import CrawlerError, NetworkError, PermanentError, TransientError, classify_http_status
from html_parser import HTMLParser
from rate_limiter import RateLimiter
from retry_strategy import RetryStrategy
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
        retry_strategy: RetryStrategy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        timeout_growth_factor: float = 1.5,
        storage: DataStorage | None = None,
        storage_max_retries: int = 2,
        storage_retry_delay: float = 0.2,
    ):
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth
        self.per_domain_limit = per_domain_limit
        self.user_agent = user_agent
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.timeout_growth_factor = timeout_growth_factor
        self.storage = storage
        self.storage_max_retries = storage_max_retries
        self.storage_retry_delay = storage_retry_delay

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: aiohttp.ClientSession | None = None
        self._parser = HTMLParser(follow_external_links=follow_external_links)
        self._rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            per_domain=per_domain_rate_limit,
            min_delay=min_delay,
            jitter=jitter,
        )
        self._robots = RobotsParser() if respect_robots else None
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}
        self.processed_urls: dict[str, dict] = {}
        self.blocked_urls: set[str] = set()
        self.circuit_open_urls: set[str] = set()
        self.storage_errors: list[str] = []

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers={"User-Agent": self.user_agent},
            )
        return self._session

    async def _do_fetch(self, url: str, domain: str, crawl_delay: float | None, attempt_timeout: float) -> dict:
        session = self._get_session()
        await self._rate_limiter.acquire(domain, min_delay=crawl_delay)
        timeout = aiohttp.ClientTimeout(connect=self.connect_timeout, sock_read=attempt_timeout)

        async with self._semaphore:
            logger.info("-> start fetching %s", url)
            try:
                # allow_redirects=False: redirects are resolved manually in _fetch_full so
                # every hop re-checks robots.txt, rate limits and circuit breaker for its
                # own domain -- otherwise a redirect could silently escape those checks.
                async with session.get(url, timeout=timeout, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise TransientError("redirect without Location header", url=url, status=response.status)
                        return {"redirect_to": urljoin(url, location)}
                    if response.status >= 400:
                        error_cls = classify_http_status(response.status)
                        raise error_cls(f"HTTP {response.status}", url=url, status=response.status)
                    text = await response.text()
                    logger.info("<- done %s (status=%s, %d bytes)", url, response.status, len(text))
                    return {
                        "text": text,
                        "status": response.status,
                        "content_type": response.content_type,
                        "redirect_to": None,
                    }
            except asyncio.TimeoutError as e:
                raise TransientError("request timed out", url=url, cause=e) from e
            except aiohttp.ClientError as e:
                raise NetworkError(str(e), url=url, cause=e) from e

    async def _fetch_one_hop(self, url: str) -> dict:
        domain = urlparse(url).netloc

        if self.circuit_breaker.is_open(domain):
            self.circuit_open_urls.add(url)
            logger.warning("circuit open for domain %s, skipping %s", domain, url)
            raise PermanentError(f"circuit open for domain {domain}", url=url)

        crawl_delay = None
        if self._robots is not None:
            if not self._robots.has_domain(domain):
                await self._robots.fetch_robots(url)
            if not self._robots.can_fetch(url, self.user_agent):
                self.blocked_urls.add(url)
                logger.warning("blocked by robots.txt: %s", url)
                raise RobotsDisallowedError(url)
            crawl_delay = self._robots.get_crawl_delay(self.user_agent, domain)

        attempt_timeouts = _timeout_schedule(self.read_timeout, self.timeout_growth_factor, self.retry_strategy.max_retries)
        attempt_counter = {"n": 0}

        async def _attempt():
            timeout = attempt_timeouts[min(attempt_counter["n"], len(attempt_timeouts) - 1)]
            attempt_counter["n"] += 1
            return await self._do_fetch(url, domain, crawl_delay, timeout)

        try:
            result = await self.retry_strategy.execute_with_retry(_attempt)
            self.circuit_breaker.record_success(domain)
            return result
        except CrawlerError:
            self.circuit_breaker.record_failure(domain)
            raise

    async def _fetch_full(self, url: str, max_redirects: int = 5) -> dict:
        current_url = url
        for _ in range(max_redirects + 1):
            result = await self._fetch_one_hop(current_url)
            redirect_to = result.get("redirect_to")
            if redirect_to is None:
                result["requested_url"] = url
                result["final_url"] = current_url
                return result
            logger.info("redirect %s -> %s", current_url, redirect_to)
            current_url = redirect_to
        raise TransientError(f"too many redirects starting at {url}", url=url)

    async def fetch_url(self, url: str) -> str:
        result = await self._fetch_full(url)
        return result["text"]

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        async def _safe_fetch(url: str):
            try:
                return url, await self.fetch_url(url)
            except (CrawlerError, RobotsDisallowedError) as e:
                return url, e

        results = await asyncio.gather(*(_safe_fetch(u) for u in urls))
        return dict(results)

    async def fetch_and_parse(self, url: str) -> dict:
        fetched = await self._fetch_full(url)
        # parse against final_url (post-redirect) so relative links resolve against the
        # page that actually served the HTML, not the originally requested URL
        record = await self._parser.parse_html(fetched["text"], fetched["final_url"])
        record["requested_url"] = fetched["requested_url"]
        record["crawled_at"] = datetime.now(timezone.utc).isoformat()
        record["status_code"] = fetched["status"]
        record["content_type"] = fetched["content_type"]

        await self._save_record(record)
        return record

    async def _save_record(self, record: dict):
        if self.storage is None:
            return
        for attempt in range(self.storage_max_retries + 1):
            try:
                await self.storage.save(record)
                return
            except Exception as e:
                if attempt >= self.storage_max_retries:
                    logger.error("giving up saving %s after %d attempts: %s", record.get("url"), attempt + 1, e)
                    self.storage_errors.append(record.get("url", ""))
                    return
                logger.warning("storage save failed for %s (attempt %d/%d): %s", record.get("url"), attempt + 1, self.storage_max_retries + 1, e)
                await asyncio.sleep(self.storage_retry_delay)

    def get_rate_stats(self) -> dict:
        return {
            "current_rate": self._rate_limiter.current_rate,
            "average_delay": self._rate_limiter.average_delay,
            "blocked_count": len(self.blocked_urls),
        }

    def get_error_stats(self) -> dict:
        summary = self.retry_strategy.stats.summary()
        summary["circuit_open_count"] = len(self.circuit_open_urls)
        summary["storage_errors"] = len(self.storage_errors)
        return summary

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
                    except (CrawlerError, aiohttp.ClientError, asyncio.TimeoutError) as e:
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
        if self.storage is not None:
            await self.storage.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()


def _timeout_schedule(base_timeout: float, growth_factor: float, max_retries: int) -> list[float]:
    return [base_timeout * (growth_factor ** i) for i in range(max_retries + 1)]
