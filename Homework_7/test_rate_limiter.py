import asyncio
import time

import pytest

from rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_same_domain_calls_are_spaced_by_interval():
    limiter = RateLimiter(requests_per_second=10, per_domain=True)
    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire("a.com")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.2 - 0.02


@pytest.mark.asyncio
async def test_different_domains_do_not_block_each_other():
    limiter = RateLimiter(requests_per_second=2, per_domain=True)
    start = time.monotonic()
    await asyncio.gather(
        limiter.acquire("a.com"),
        limiter.acquire("b.com"),
        limiter.acquire("c.com"),
    )
    elapsed = time.monotonic() - start
    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_global_limit_applies_across_domains():
    limiter = RateLimiter(requests_per_second=10, per_domain=False)
    start = time.monotonic()
    await limiter.acquire("a.com")
    await limiter.acquire("b.com")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1 - 0.02


@pytest.mark.asyncio
async def test_min_delay_override_extends_wait():
    limiter = RateLimiter(requests_per_second=100, per_domain=True)
    await limiter.acquire("a.com")
    start = time.monotonic()
    await limiter.acquire("a.com", min_delay=0.15)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.15 - 0.02


@pytest.mark.asyncio
async def test_average_delay_and_current_rate_are_tracked():
    limiter = RateLimiter(requests_per_second=20, per_domain=True)
    for _ in range(3):
        await limiter.acquire("a.com")
    assert limiter.average_delay >= 0
    assert limiter.current_rate > 0
