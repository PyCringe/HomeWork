import asyncio
import logging

import aiohttp

logger = logging.getLogger("async_crawler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class AsyncCrawler:
    def __init__(
        self,
        max_concurrent: int = 10,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = aiohttp.ClientTimeout(
            connect=connect_timeout,
            sock_read=read_timeout,
        )
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=connector,
            )
        return self._session

    async def fetch_url(self, url: str) -> str:
        session = self._get_session()
        async with self._semaphore:
            logger.info("-> start fetching %s", url)
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    text = await response.text()
                    logger.info("<- done %s (status=%s, %d bytes)", url, response.status, len(text))
                    return text
            except asyncio.TimeoutError:
                logger.warning("timeout fetching %s", url)
                raise
            except aiohttp.ClientResponseError as e:
                logger.warning("HTTP %s on %s: %s", e.status, url, e.message)
                raise
            except aiohttp.ClientError as e:
                logger.warning("network error on %s: %s", url, type(e).__name__)
                raise

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        async def _safe_fetch(url: str):
            try:
                return url, await self.fetch_url(url)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                return url, e

        results = await asyncio.gather(*(_safe_fetch(u) for u in urls))
        return dict(results)

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()
