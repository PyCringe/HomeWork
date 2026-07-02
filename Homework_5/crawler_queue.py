import heapq
import itertools


class CrawlerQueue:
    def __init__(self):
        self._heap = []
        self._counter = itertools.count()
        self._queued = set()
        self._depths = {}
        self._processed = set()
        self._failed = {}

    def add_url(self, url: str, priority: int = 0, depth: int = 0) -> bool:
        if url in self._queued:
            return False
        heapq.heappush(self._heap, (-priority, next(self._counter), url))
        self._queued.add(url)
        self._depths.setdefault(url, depth)
        return True

    async def get_next(self) -> str | None:
        if not self._heap:
            return None
        _, _, url = heapq.heappop(self._heap)
        self._queued.discard(url)
        return url

    def get_depth(self, url: str) -> int:
        return self._depths.get(url, 0)

    def mark_processed(self, url: str):
        self._processed.add(url)

    def mark_failed(self, url: str, error: str):
        self._failed[url] = error

    def get_stats(self) -> dict:
        return {
            "queued": len(self._heap),
            "processed": len(self._processed),
            "failed": len(self._failed),
        }
