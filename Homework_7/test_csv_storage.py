import csv

import pytest

from csv_storage import CSVStorage

RECORD_A = {
    "url": "https://a.com",
    "title": "Simple, title",
    "text": "hello world",
    "links": ["https://a.com/x"],
    "metadata": {"description": 'has "quotes" and, commas'},
    "crawled_at": "2026-01-01T00:00:00+00:00",
    "status_code": 200,
    "content_type": "text/html",
}
RECORD_B = {
    "url": "https://b.com",
    "title": "Multi\nline\ntitle",
    "text": "world",
    "links": [],
    "metadata": {},
    "crawled_at": "2026-01-01T00:01:00+00:00",
    "status_code": 200,
    "content_type": "text/html",
}


@pytest.mark.asyncio
async def test_header_written_once(tmp_path):
    path = str(tmp_path / "out.csv")
    storage = CSVStorage(path)
    await storage.save(RECORD_A)
    await storage.save(RECORD_B)
    await storage.close()

    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["url", "title", "text", "links", "metadata", "crawled_at", "status_code", "content_type"]
    assert len(rows) == 3  # header + 2 records


@pytest.mark.asyncio
async def test_special_characters_round_trip(tmp_path):
    path = str(tmp_path / "out.csv")
    storage = CSVStorage(path)
    await storage.save(RECORD_A)
    await storage.save(RECORD_B)

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert rows[0]["title"] == "Simple, title"
    assert rows[1]["title"] == "Multi\nline\ntitle"


@pytest.mark.asyncio
async def test_links_and_metadata_are_json_encoded(tmp_path):
    import json

    path = str(tmp_path / "out.csv")
    storage = CSVStorage(path)
    await storage.save(RECORD_A)

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    assert json.loads(row["links"]) == ["https://a.com/x"]
    assert json.loads(row["metadata"])["description"] == 'has "quotes" and, commas'


@pytest.mark.asyncio
async def test_resumes_without_rewriting_header_if_file_exists(tmp_path):
    path = str(tmp_path / "out.csv")
    await CSVStorage(path).save(RECORD_A)

    storage2 = CSVStorage(path)
    await storage2.save(RECORD_B)

    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["url", "title", "text", "links", "metadata", "crawled_at", "status_code", "content_type"]
    assert len(rows) == 3
