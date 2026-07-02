import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlparse


class SemaphoreManager:
    def __init__(self, global_limit: int = 10, per_domain_limit: int = 2):
        self.global_limit = global_limit
        self.per_domain_limit = per_domain_limit
        self._global = asyncio.Semaphore(global_limit)
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        self._active = 0

    def _domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(self.per_domain_limit)
        return self._domain_semaphores[domain]

    @asynccontextmanager
    async def acquire(self, url: str):
        domain = urlparse(url).netloc
        domain_sem = self._domain_semaphore(domain)
        async with self._global, domain_sem:
            self._active += 1
            try:
                yield
            finally:
                self._active -= 1

    @property
    def active_count(self) -> int:
        return self._active
