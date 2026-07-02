class CrawlerError(Exception):
    def __init__(self, message: str, url: str | None = None, status: int | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.url = url
        self.status = status
        self.cause = cause


class TransientError(CrawlerError):
    pass


class PermanentError(CrawlerError):
    pass


class NetworkError(CrawlerError):
    pass


class ParseError(CrawlerError):
    pass


_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
_PERMANENT_STATUSES = {401, 403, 404}


def classify_http_status(status: int) -> type[CrawlerError]:
    if status in _TRANSIENT_STATUSES:
        return TransientError
    if status in _PERMANENT_STATUSES:
        return PermanentError
    if status >= 500:
        return TransientError
    if status >= 400:
        return PermanentError
    return TransientError
