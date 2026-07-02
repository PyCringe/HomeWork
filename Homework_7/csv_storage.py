import asyncio
import csv
import io
import json
import os

import aiofiles

from data_storage import DataStorage

FIELDNAMES = ["url", "title", "text", "links", "metadata", "crawled_at", "status_code", "content_type"]
TEXT_PREVIEW_LENGTH = 500


class CSVStorage(DataStorage):
    def __init__(self, path: str, encoding: str = "utf-8"):
        self.path = path
        self.encoding = encoding
        self._lock = asyncio.Lock()
        self._header_written = os.path.exists(path) and os.path.getsize(path) > 0

    def _row_from_data(self, data: dict) -> dict:
        text = data.get("text") or ""
        return {
            "url": data.get("url", ""),
            "title": data.get("title") or "",
            "text": text[:TEXT_PREVIEW_LENGTH],
            "links": json.dumps(data.get("links", []), ensure_ascii=False),
            "metadata": json.dumps(data.get("metadata", {}), ensure_ascii=False),
            "crawled_at": data.get("crawled_at", ""),
            "status_code": data.get("status_code", ""),
            "content_type": data.get("content_type", ""),
        }

    async def save(self, data: dict):
        row = self._row_from_data(data)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES)

        async with self._lock:
            if not self._header_written:
                writer.writeheader()
                self._header_written = True
            writer.writerow(row)
            async with aiofiles.open(self.path, mode="a", encoding=self.encoding, newline="") as f:
                await f.write(buffer.getvalue())

    async def close(self):
        pass
