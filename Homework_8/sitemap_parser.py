import logging

import aiohttp
import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

logger = logging.getLogger("sitemap_parser")

MAX_SITEMAP_BYTES = 20_000_000
MAX_SITEMAP_DEPTH = 5


class SitemapParser:
    def __init__(self, fetcher=None):
        self._fetcher = fetcher
        self._own_session: aiohttp.ClientSession | None = None

    async def _fetch_text(self, url: str) -> str | None:
        if self._fetcher is not None:
            try:
                return await self._fetcher(url)
            except Exception:
                return None

        if self._own_session is None or self._own_session.closed:
            self._own_session = aiohttp.ClientSession()
        try:
            # allow_redirects=False for the same reason as robots.txt fetches: a
            # redirect could point at an unrelated origin's sitemap.
            async with self._own_session.get(url, allow_redirects=False) as response:
                if response.status >= 400 or response.status in (301, 302, 303, 307, 308):
                    return None
                raw = await response.content.read(MAX_SITEMAP_BYTES + 1)
                if len(raw) > MAX_SITEMAP_BYTES:
                    logger.warning("sitemap %s exceeds size limit, skipping", url)
                    return None
                return raw.decode(response.get_encoding(), errors="replace")
        except aiohttp.ClientError:
            return None

    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        return await self._fetch_recursive(sitemap_url, seen=set(), depth=0)

    async def _fetch_recursive(self, url: str, seen: set, depth: int) -> list[str]:
        if url in seen or depth > MAX_SITEMAP_DEPTH:
            return []
        seen.add(url)

        text = await self._fetch_text(url)
        if text is None:
            logger.warning("failed to fetch sitemap %s", url)
            return []

        try:
            # defusedxml rejects DTDs, external entities and entity expansion bombs
            # outright -- sitemap.xml is untrusted input fetched over the network.
            root = ET.fromstring(text)
        except DefusedXmlException as e:
            logger.warning("rejected unsafe sitemap XML at %s: %s", url, e)
            return []
        except ET.ParseError as e:
            logger.warning("invalid sitemap XML at %s: %s", url, e)
            return []

        tag = _local_name(root.tag)
        urls: list[str] = []

        if tag == "sitemapindex":
            child_urls = [loc.text.strip() for loc in root.findall(".//{*}loc") if loc.text]
            for child_url in child_urls:
                urls.extend(await self._fetch_recursive(child_url, seen, depth + 1))
        elif tag == "urlset":
            urls.extend(loc.text.strip() for loc in root.findall(".//{*}loc") if loc.text)
        else:
            logger.warning("unrecognized sitemap root element <%s> at %s", tag, url)

        return urls

    async def close(self):
        if self._own_session is not None and not self._own_session.closed:
            await self._own_session.close()
            self._own_session = None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag
