import time
from collections import defaultdict


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_time: float = 30.0, window: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.window = window
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._opened_at: dict[str, float] = {}

    def record_failure(self, domain: str):
        now = time.monotonic()
        recent = [t for t in self._failures[domain] if now - t < self.window]
        recent.append(now)
        self._failures[domain] = recent
        if len(recent) >= self.failure_threshold:
            self._opened_at[domain] = now

    def record_success(self, domain: str):
        self._failures[domain] = []
        self._opened_at.pop(domain, None)

    def is_open(self, domain: str) -> bool:
        opened_at = self._opened_at.get(domain)
        if opened_at is None:
            return False
        if time.monotonic() - opened_at >= self.recovery_time:
            self._opened_at.pop(domain, None)
            self._failures[domain] = []
            return False
        return True
