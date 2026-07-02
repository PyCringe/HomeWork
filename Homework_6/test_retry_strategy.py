import time

import pytest

from errors import NetworkError, PermanentError, TransientError
from retry_strategy import RetryStrategy


@pytest.mark.asyncio
async def test_retries_transient_error_until_success():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("503", url="https://a.com", status=503)
        return "ok"

    strategy = RetryStrategy(max_retries=5, base_delay=0.01, backoff_factor=1.5)
    result = await strategy.execute_with_retry(flaky)

    assert result == "ok"
    assert calls["n"] == 3
    assert strategy.stats.successful_retries == 1


@pytest.mark.asyncio
async def test_retries_network_error():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise NetworkError("connection refused", url="https://a.com")
        return "ok"

    strategy = RetryStrategy(max_retries=3, base_delay=0.01)
    result = await strategy.execute_with_retry(flaky)

    assert result == "ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_does_not_retry_permanent_error():
    calls = {"n": 0}

    async def always_404():
        calls["n"] += 1
        raise PermanentError("404", url="https://a.com", status=404)

    strategy = RetryStrategy(max_retries=5, base_delay=0.01)
    with pytest.raises(PermanentError):
        await strategy.execute_with_retry(always_404)

    assert calls["n"] == 1
    assert strategy.stats.permanent_failures == ["https://a.com"]


@pytest.mark.asyncio
async def test_gives_up_after_max_retries():
    calls = {"n": 0}

    async def always_503():
        calls["n"] += 1
        raise TransientError("503", url="https://a.com", status=503)

    strategy = RetryStrategy(max_retries=2, base_delay=0.01)
    with pytest.raises(TransientError):
        await strategy.execute_with_retry(always_503)

    assert calls["n"] == 3  # initial attempt + 2 retries
    assert strategy.stats.errors_by_type["TransientError"] == 3


@pytest.mark.asyncio
async def test_backoff_grows_exponentially():
    calls = {"n": 0}
    timestamps = []

    async def always_503():
        timestamps.append(time.monotonic())
        calls["n"] += 1
        raise TransientError("503", url="https://a.com", status=503)

    strategy = RetryStrategy(max_retries=2, base_delay=0.05, backoff_factor=2.0)
    with pytest.raises(TransientError):
        await strategy.execute_with_retry(always_503)

    first_gap = timestamps[1] - timestamps[0]
    second_gap = timestamps[2] - timestamps[1]
    assert second_gap > first_gap


@pytest.mark.asyncio
async def test_custom_retry_on_narrows_retryable_types():
    calls = {"n": 0}

    async def flaky_network():
        calls["n"] += 1
        raise NetworkError("dns failure", url="https://a.com")

    strategy = RetryStrategy(max_retries=3, base_delay=0.01, retry_on=[TransientError])
    with pytest.raises(NetworkError):
        await strategy.execute_with_retry(flaky_network)

    assert calls["n"] == 1
