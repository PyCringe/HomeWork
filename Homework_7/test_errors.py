from errors import NetworkError, PermanentError, TransientError, classify_http_status


def test_transient_statuses():
    assert classify_http_status(429) is TransientError
    assert classify_http_status(503) is TransientError
    assert classify_http_status(500) is TransientError
    assert classify_http_status(502) is TransientError


def test_permanent_statuses():
    assert classify_http_status(404) is PermanentError
    assert classify_http_status(403) is PermanentError
    assert classify_http_status(401) is PermanentError


def test_error_carries_url_and_status():
    err = TransientError("HTTP 503", url="https://a.com", status=503)
    assert err.url == "https://a.com"
    assert err.status == 503


def test_network_error_is_distinct_type():
    err = NetworkError("connection refused", url="https://a.com")
    assert isinstance(err, NetworkError)
    assert not isinstance(err, TransientError)
