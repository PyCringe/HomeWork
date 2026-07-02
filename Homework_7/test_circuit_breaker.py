from circuit_breaker import CircuitBreaker


def test_circuit_stays_closed_below_threshold():
    breaker = CircuitBreaker(failure_threshold=3, window=60.0)
    breaker.record_failure("a.com")
    breaker.record_failure("a.com")
    assert breaker.is_open("a.com") is False


def test_circuit_opens_at_threshold():
    breaker = CircuitBreaker(failure_threshold=3, window=60.0)
    for _ in range(3):
        breaker.record_failure("a.com")
    assert breaker.is_open("a.com") is True


def test_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3, window=60.0)
    breaker.record_failure("a.com")
    breaker.record_failure("a.com")
    breaker.record_success("a.com")
    breaker.record_failure("a.com")
    assert breaker.is_open("a.com") is False


def test_circuit_recovers_after_recovery_time():
    breaker = CircuitBreaker(failure_threshold=1, recovery_time=0.0, window=60.0)
    breaker.record_failure("a.com")
    assert breaker.is_open("a.com") is False


def test_domains_are_independent():
    breaker = CircuitBreaker(failure_threshold=2, window=60.0)
    breaker.record_failure("a.com")
    breaker.record_failure("a.com")
    assert breaker.is_open("a.com") is True
    assert breaker.is_open("b.com") is False
