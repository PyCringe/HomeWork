import asyncio
import random
import time


class RateLimiter:
    def __init__(
        self,
        requests_per_second: float = 1.0,
        per_domain: bool = True,
        min_delay: float = 0.0,
        jitter: float = 0.0,
    ):
        self.requests_per_second = requests_per_second
        self.per_domain = per_domain
        self.min_delay = min_delay
        self.jitter = jitter
        self._interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._delays: list[float] = []
        self._request_count = 0
        self._start_time: float | None = None

    def _key(self, domain: str | None) -> str:
        return domain if self.per_domain and domain else "__global__"

    def _lock_for(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def acquire(self, domain: str | None = None, min_delay: float | None = None):
        key = self._key(domain)
        required = max(self._interval, self.min_delay, min_delay or 0.0)

        async with self._lock_for(key):
            now = time.monotonic()
            last = self._last_request.get(key)
            wait = required - (now - last) if last is not None else 0.0
            if wait < 0:
                wait = 0.0
            if self.jitter > 0:
                wait += random.uniform(0, self.jitter)

            if wait > 0:
                await asyncio.sleep(wait)

            self._last_request[key] = time.monotonic()
            self._delays.append(wait)
            self._request_count += 1
            if self._start_time is None:
                self._start_time = time.monotonic()

    @property
    def current_rate(self) -> float:
        if not self._start_time or self._request_count == 0:
            return 0.0
        elapsed = time.monotonic() - self._start_time
        return self._request_count / elapsed if elapsed > 0 else 0.0

    @property
    def average_delay(self) -> float:
        if not self._delays:
            return 0.0
        return sum(self._delays) / len(self._delays)
