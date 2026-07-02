import json

import pytest

from config import CrawlerConfig


def test_from_json_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "start_urls": ["https://a.com"],
        "max_pages": 42,
        "requests_per_second": 3.5,
    }), encoding="utf-8")

    config = CrawlerConfig.from_file(str(path))
    assert config.start_urls == ["https://a.com"]
    assert config.max_pages == 42
    assert config.requests_per_second == 3.5
    assert config.max_depth == 2  # default preserved


def test_from_yaml_file(tmp_path):
    yaml = pytest.importorskip("yaml")
    path = tmp_path / "config.yaml"
    path.write_text(
        "start_urls:\n  - https://a.com\nmax_pages: 10\nrespect_robots: false\n",
        encoding="utf-8",
    )

    config = CrawlerConfig.from_file(str(path))
    assert config.start_urls == ["https://a.com"]
    assert config.max_pages == 10
    assert config.respect_robots is False


def test_unknown_key_raises(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"totally_made_up_field": 1}), encoding="utf-8")

    with pytest.raises(ValueError):
        CrawlerConfig.from_file(str(path))


def test_empty_json_file_uses_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("", encoding="utf-8")

    config = CrawlerConfig.from_file(str(path))
    assert config.max_pages == 100


def test_to_dict_round_trips_fields():
    config = CrawlerConfig(start_urls=["https://a.com"], max_pages=5)
    data = config.to_dict()
    assert data["start_urls"] == ["https://a.com"]
    assert data["max_pages"] == 5
