import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp

logger = logging.getLogger("robots_parser")


class RobotsParser:
    def __init__(self, fetcher=None):
        self._fetcher = fetcher
        self._own_session: aiohttp.ClientSession | None = None
        self._cache: dict[str, RobotFileParser] = {}

    def has_domain(self, domain: str) -> bool:
        return domain in self._cache

    async def _fetch_text(self, url: str) -> str | None:
        if self._fetcher is not None:
            try:
                return await self._fetcher(url)
            except Exception:
                return None

        if self._own_session is None or self._own_session.closed:
            self._own_session = aiohttp.ClientSession()
        try:
            # allow_redirects=False: a redirect could point robots.txt fetches at a
            # different origin, letting that origin's operator define crawl policy for
            # a domain it doesn't control. Treat any redirect as "no robots.txt", same
            # as a 404 -- per RFC 9309 SS2.3.1.2, redirects are not guaranteed to be honored.
            async with self._own_session.get(url, allow_redirects=False) as response:
                if response.status >= 400 or response.status in (301, 302, 303, 307, 308):
                    return None
                return await response.text()
        except aiohttp.ClientError:
            return None

    async def fetch_robots(self, base_url: str) -> dict:
        parsed = urlparse(base_url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        text = await self._fetch_text(robots_url)

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines() if text is not None else [])
        self._cache[domain] = parser

        if text is None:
            logger.info("no robots.txt for %s, allowing all", domain)

        return {
            "domain": domain,
            "fetched": text is not None,
            "crawl_delay": parser.crawl_delay("*"),
        }

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        domain = urlparse(url).netloc
        parser = self._cache.get(domain)
        if parser is None:
            return True
        return parser.can_fetch(user_agent, url)

    def get_crawl_delay(self, user_agent: str = "*", domain: str | None = None) -> float:
        parser = self._cache.get(domain) if domain else None
        if parser is None:
            return 0.0
        delay = parser.crawl_delay(user_agent)
        return delay if delay is not None else 0.0

    async def close(self):
        if self._own_session is not None and not self._own_session.closed:
            await self._own_session.close()
            self._own_session = None
