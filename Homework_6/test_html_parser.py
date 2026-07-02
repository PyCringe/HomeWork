import pytest

from html_parser import HTMLParser

VALID_HTML = """
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="A test page">
    <meta name="keywords" content="test, page">
</head>
<body>
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>
    <p>Some body text.</p>
    <a href="/relative/page">Relative link</a>
    <a href="https://external.com/page">External link</a>
    <a href="mailto:someone@example.com">Mail link</a>
    <img src="/img/logo.png" alt="Logo">
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <table>
        <tr><th>Name</th><th>Age</th></tr>
        <tr><td>Alice</td><td>30</td></tr>
    </table>
</body>
</html>
"""

BASE_URL = "https://example.com/section/page.html"


@pytest.fixture
def parser():
    return HTMLParser()


@pytest.mark.asyncio
async def test_parse_html_returns_full_structure(parser):
    result = await parser.parse_html(VALID_HTML, BASE_URL)
    assert result["url"] == BASE_URL
    assert result["title"] == "Test Page"
    assert "Some body text." in result["text"]
    assert result["metadata"]["description"] == "A test page"
    assert result["metadata"]["keywords"] == "test, page"


@pytest.mark.asyncio
async def test_parse_broken_html_returns_partial_result(parser):
    broken = "<html><body><p>Unclosed paragraph<div>nested</p></body>"
    result = await parser.parse_html(broken, BASE_URL)
    assert result["url"] == BASE_URL
    assert isinstance(result["text"], str)


@pytest.mark.asyncio
async def test_parse_empty_string_does_not_raise(parser):
    result = await parser.parse_html("", BASE_URL)
    assert result["links"] == []
    assert result["title"] is None


def test_extract_links_converts_relative_to_absolute(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    links = parser.extract_links(soup, BASE_URL)
    assert "https://example.com/relative/page" in links
    assert "https://external.com/page" in links


def test_extract_links_filters_non_http_schemes(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    links = parser.extract_links(soup, BASE_URL)
    assert not any(link.startswith("mailto:") for link in links)


def test_extract_links_excludes_external_when_disabled():
    from bs4 import BeautifulSoup

    internal_only_parser = HTMLParser(follow_external_links=False)
    soup = BeautifulSoup(VALID_HTML, "lxml")
    links = internal_only_parser.extract_links(soup, BASE_URL)
    assert all("external.com" not in link for link in links)
    assert "https://example.com/relative/page" in links


def test_extract_metadata(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    metadata = parser.extract_metadata(soup)
    assert metadata["title"] == "Test Page"
    assert metadata["description"] == "A test page"


def test_extract_images_resolves_relative_src(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    images = parser.extract_images(soup, BASE_URL)
    assert images == [{"src": "https://example.com/img/logo.png", "alt": "Logo"}]


def test_extract_headings(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    headings = parser.extract_headings(soup)
    assert headings["h1"] == ["Main Heading"]
    assert headings["h2"] == ["Sub Heading"]
    assert headings["h3"] == []


def test_extract_lists(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    lists = parser.extract_lists(soup)
    assert lists == [["Item 1", "Item 2"]]


def test_extract_tables(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    tables = parser.extract_tables(soup)
    assert tables == [[["Name", "Age"], ["Alice", "30"]]]


def test_extract_text_with_selector(parser):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(VALID_HTML, "lxml")
    text = parser.extract_text(soup, selector="h1")
    assert text == "Main Heading"
