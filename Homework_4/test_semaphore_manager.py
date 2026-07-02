import asyncio

import pytest

from semaphore_manager import SemaphoreManager


@pytest.mark.asyncio
async def test_global_limit_caps_active_count():
    manager = SemaphoreManager(global_limit=2, per_domain_limit=5)
    peak = 0

    async def task(url):
        nonlocal peak
        async with manager.acquire(url):
            peak = max(peak, manager.active_count)
            await asyncio.sleep(0.1)

    urls = [f"https://site{i}.com" for i in range(5)]
    await asyncio.gather(*(task(u) for u in urls))
    assert peak <= 2


@pytest.mark.asyncio
async def test_per_domain_limit_caps_same_domain_concurrency():
    manager = SemaphoreManager(global_limit=10, per_domain_limit=1)
    peak = 0

    async def task():
        nonlocal peak
        async with manager.acquire("https://same-domain.com/page"):
            peak = max(peak, manager.active_count)
            await asyncio.sleep(0.1)

    await asyncio.gather(*(task() for _ in range(4)))
    assert peak <= 1


@pytest.mark.asyncio
async def test_active_count_returns_to_zero_after_completion():
    manager = SemaphoreManager()
    async with manager.acquire("https://a.com"):
        assert manager.active_count == 1
    assert manager.active_count == 0
