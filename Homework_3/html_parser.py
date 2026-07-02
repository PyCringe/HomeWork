import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger("html_parser")


class HTMLParser:
    def __init__(self, follow_external_links: bool = True):
        self.follow_external_links = follow_external_links

    async def parse_html(self, html: str, url: str) -> dict:
        result = {
            "url": url,
            "title": None,
            "text": "",
            "links": [],
            "images": [],
            "headings": {"h1": [], "h2": [], "h3": []},
            "tables": [],
            "lists": [],
            "metadata": {},
        }

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            logger.warning("failed to parse HTML for %s: %s", url, e)
            return result

        extractors = {
            "metadata": lambda: self.extract_metadata(soup),
            "text": lambda: self.extract_text(soup),
            "links": lambda: self.extract_links(soup, url),
            "images": lambda: self.extract_images(soup, url),
            "headings": lambda: self.extract_headings(soup),
            "tables": lambda: self.extract_tables(soup),
            "lists": lambda: self.extract_lists(soup),
        }
        for field, extractor in extractors.items():
            try:
                result[field] = extractor()
            except Exception as e:
                logger.warning("failed to extract %s for %s: %s", field, url, e)

        result["title"] = result["metadata"].get("title")
        return result

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        base_netloc = urlparse(base_url).netloc
        seen = set()
        links = []
        for tag in soup.find_all("a", href=True):
            absolute = urljoin(base_url, tag["href"].strip())
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                continue
            if not self.follow_external_links and parsed.netloc != base_netloc:
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            links.append(absolute)
        return links

    def extract_text(self, soup: BeautifulSoup, selector: str = None) -> str:
        if selector:
            nodes = soup.select(selector)
            return "\n".join(node.get_text(strip=True) for node in nodes)
        return soup.get_text(separator=" ", strip=True)

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        title_tag = soup.find("title")
        description_tag = soup.find("meta", attrs={"name": "description"})
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        return {
            "title": title_tag.get_text(strip=True) if title_tag else None,
            "description": description_tag.get("content") if description_tag else None,
            "keywords": keywords_tag.get("content") if keywords_tag else None,
        }

    def extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images = []
        for tag in soup.find_all("img"):
            src = tag.get("src")
            if not src:
                continue
            images.append({
                "src": urljoin(base_url, src.strip()),
                "alt": tag.get("alt", ""),
            })
        return images

    def extract_headings(self, soup: BeautifulSoup) -> dict:
        return {
            level: [tag.get_text(strip=True) for tag in soup.find_all(level)]
            for level in ("h1", "h2", "h3")
        }

    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables = []
        for table_tag in soup.find_all("table"):
            rows = []
            for row_tag in table_tag.find_all("tr"):
                cells = [cell.get_text(strip=True) for cell in row_tag.find_all(("td", "th"))]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    def extract_lists(self, soup: BeautifulSoup) -> list[list[str]]:
        lists = []
        for list_tag in soup.find_all(("ul", "ol")):
            items = [li.get_text(strip=True) for li in list_tag.find_all("li", recursive=False)]
            if items:
                lists.append(items)
        return lists
