import asyncio
import logging
import time

from errors import CrawlerError, NetworkError, TransientError
from retry_stats import RetryStats

logger = logging.getLogger("retry_strategy")


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_on: list[type[CrawlerError]] | None = None,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = tuple(retry_on) if retry_on else (TransientError, NetworkError)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.stats = RetryStats()

    def _compute_delay(self, error: CrawlerError, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** attempt)
        if getattr(error, "status", None) == 429:
            delay *= 2
        return min(delay, self.max_delay)

    async def execute_with_retry(self, coro, *args, **kwargs):
        start = time.monotonic()
        attempt = 0

        while True:
            try:
                result = await coro(*args, **kwargs)
                if attempt > 0:
                    self.stats.record_retry_success()
                    self.stats.record_retry_duration(time.monotonic() - start)
                return result
            except CrawlerError as e:
                self.stats.record_error(e)
                retryable = isinstance(e, self.retry_on)
                if not retryable or attempt >= self.max_retries:
                    self.stats.record_permanent_failure(e)
                    if attempt > 0:
                        self.stats.record_retry_duration(time.monotonic() - start)
                    raise

                delay = self._compute_delay(e, attempt)
                logger.warning(
                    "attempt %d/%d failed for %s (%s), retrying in %.2fs",
                    attempt + 1, self.max_retries, e.url, type(e).__name__, delay,
                )
                await asyncio.sleep(delay)
                attempt += 1
