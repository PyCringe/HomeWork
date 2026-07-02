import asyncio

import pytest

from data_storage import JSONStorage, read_json_array, read_json_lines

RECORD_A = {"url": "https://a.com", "title": "A", "text": "hello", "links": ["https://a.com/x"], "metadata": {}}
RECORD_B = {"url": "https://b.com", "title": "Кириллица и émojis 🎉", "text": "world", "links": [], "metadata": {"k": "v"}}


@pytest.mark.asyncio
async def test_save_and_read_roundtrip(tmp_path):
    path = str(tmp_path / "out.jsonl")
    storage = JSONStorage(path)
    await storage.save(RECORD_A)
    await storage.save(RECORD_B)
    await storage.close()

    records = await read_json_lines(path)
    assert records == [RECORD_A, RECORD_B]


@pytest.mark.asyncio
async def test_unicode_is_preserved(tmp_path):
    path = str(tmp_path / "out.jsonl")
    storage = JSONStorage(path)
    await storage.save(RECORD_B)

    records = await read_json_lines(path)
    assert records[0]["title"] == "Кириллица и émojis 🎉"


@pytest.mark.asyncio
async def test_concurrent_saves_do_not_interleave(tmp_path):
    path = str(tmp_path / "out.jsonl")
    storage = JSONStorage(path)
    records = [{"url": f"https://x.com/{i}", "title": f"page {i}"} for i in range(20)]

    await asyncio.gather(*(storage.save(r) for r in records))

    saved = await read_json_lines(path)
    assert len(saved) == 20
    assert {r["url"] for r in saved} == {r["url"] for r in records}


@pytest.mark.asyncio
async def test_array_mode_produces_formatted_readable_array(tmp_path):
    path = str(tmp_path / "out.json")
    storage = JSONStorage(path, mode="array")
    await storage.save(RECORD_A)
    await storage.save(RECORD_B)

    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "\n  " in content  # indented

    records = await read_json_array(path)
    assert records == [RECORD_A, RECORD_B]


def test_invalid_mode_rejected(tmp_path):
    with pytest.raises(ValueError):
        JSONStorage(str(tmp_path / "out.json"), mode="xml")
