from collections import defaultdict


class RetryStats:
    def __init__(self):
        self.errors_by_type: dict[str, int] = defaultdict(int)
        self.successful_retries = 0
        self.permanent_failures: list[str] = []
        self.retry_durations: list[float] = []

    def record_error(self, error: Exception):
        self.errors_by_type[type(error).__name__] += 1

    def record_retry_success(self):
        self.successful_retries += 1

    def record_permanent_failure(self, error: Exception):
        url = getattr(error, "url", None)
        if url:
            self.permanent_failures.append(url)

    def record_retry_duration(self, seconds: float):
        self.retry_durations.append(seconds)

    @property
    def average_retry_time(self) -> float:
        if not self.retry_durations:
            return 0.0
        return sum(self.retry_durations) / len(self.retry_durations)

    def summary(self) -> dict:
        return {
            "errors_by_type": dict(self.errors_by_type),
            "successful_retries": self.successful_retries,
            "permanent_failures": list(self.permanent_failures),
            "average_retry_time": self.average_retry_time,
        }
