import pytest

from crawler_queue import CrawlerQueue


@pytest.mark.asyncio
async def test_get_next_respects_priority():
    queue = CrawlerQueue()
    queue.add_url("https://a.com", priority=0)
    queue.add_url("https://b.com", priority=5)
    queue.add_url("https://c.com", priority=1)

    order = [await queue.get_next() for _ in range(3)]
    assert order == ["https://b.com", "https://c.com", "https://a.com"]


@pytest.mark.asyncio
async def test_get_next_returns_none_when_empty():
    queue = CrawlerQueue()
    assert await queue.get_next() is None


def test_add_url_dedups():
    queue = CrawlerQueue()
    assert queue.add_url("https://a.com") is True
    assert queue.add_url("https://a.com") is False
    assert queue.get_stats()["queued"] == 1


def test_get_depth_tracks_added_depth():
    queue = CrawlerQueue()
    queue.add_url("https://a.com", depth=3)
    assert queue.get_depth("https://a.com") == 3
    assert queue.get_depth("https://unknown.com") == 0


def test_mark_processed_and_failed_update_stats():
    queue = CrawlerQueue()
    queue.add_url("https://a.com")
    queue.add_url("https://b.com")
    queue.mark_processed("https://a.com")
    queue.mark_failed("https://b.com", "timeout")

    stats = queue.get_stats()
    assert stats["processed"] == 1
    assert stats["failed"] == 1
