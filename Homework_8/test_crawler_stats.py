import json
import time

from crawler_stats import CrawlerStats


def test_record_success_updates_counters():
    stats = CrawlerStats()
    stats.record_success("https://a.com/1", 200)
    stats.record_success("https://a.com/2", 200)
    stats.record_success("https://b.com/1", 301)

    assert stats.total_pages == 3
    assert stats.successful == 3
    assert stats.failed == 0
    assert stats.status_codes == {200: 2, 301: 1}
    assert stats.domain_counts == {"a.com": 2, "b.com": 1}


def test_record_failure_updates_counters():
    stats = CrawlerStats()
    stats.record_failure("https://a.com/1", 404)
    stats.record_failure("https://a.com/2")

    assert stats.total_pages == 2
    assert stats.failed == 2
    assert stats.status_codes == {404: 1}


def test_top_domains_sorted_descending():
    stats = CrawlerStats()
    for _ in range(5):
        stats.record_success("https://busy.com/x", 200)
    for _ in range(2):
        stats.record_success("https://quiet.com/x", 200)
    stats.record_success("https://rare.com/x", 200)

    top = stats.top_domains(n=2)
    assert top == [("busy.com", 5), ("quiet.com", 2)]


def test_pages_per_second_after_stop():
    stats = CrawlerStats()
    stats.start()
    time.sleep(0.05)
    stats.record_success("https://a.com", 200)
    stats.stop()

    assert stats.elapsed_seconds >= 0.05
    assert stats.pages_per_second > 0


def test_export_to_json_writes_valid_summary(tmp_path):
    stats = CrawlerStats()
    stats.start()
    stats.record_success("https://a.com", 200)
    stats.record_failure("https://b.com", 500)
    stats.stop()

    path = str(tmp_path / "stats.json")
    stats.export_to_json(path)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_pages"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert data["status_codes"] == {"200": 1, "500": 1}


def test_export_to_html_report_contains_key_figures(tmp_path):
    stats = CrawlerStats()
    stats.start()
    stats.record_success("https://a.com", 200)
    stats.stop()

    path = str(tmp_path / "report.html")
    stats.export_to_html_report(path)

    with open(path, encoding="utf-8") as f:
        content = f.read()

    assert "<html" in content
    assert "a.com" in content
    assert "200" in content


def test_export_to_html_report_escapes_domain():
    from crawler_stats import _render_html_report

    summary = {
        "total_pages": 1, "successful": 1, "failed": 0,
        "pages_per_second": 1.0, "elapsed_seconds": 1.0,
        "status_codes": {200: 1},
        "top_domains": [("<script>evil.com</script>", 1)],
    }
    html = _render_html_report(summary)
    assert "<script>evil.com</script>" not in html
    assert "&lt;script&gt;" in html
