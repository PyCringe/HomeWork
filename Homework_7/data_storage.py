import asyncio
import json
import os
from abc import ABC, abstractmethod

import aiofiles


class DataStorage(ABC):
    @abstractmethod
    async def save(self, data: dict):
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        raise NotImplementedError


class JSONStorage(DataStorage):
    """mode="lines" appends one compact JSON object per line (JSON Lines), good for
    large/streaming data. mode="array" keeps the file as a single formatted JSON array,
    rewritten on every save -- readable by humans but O(n) per write."""

    def __init__(self, path: str, mode: str = "lines"):
        if mode not in ("lines", "array"):
            raise ValueError("mode must be 'lines' or 'array'")
        self.path = path
        self.mode = mode
        self._lock = asyncio.Lock()

    async def save(self, data: dict):
        async with self._lock:
            if self.mode == "lines":
                await self._append_line(data)
            else:
                await self._rewrite_array(data)

    async def _append_line(self, data: dict):
        line = json.dumps(data, ensure_ascii=False)
        async with aiofiles.open(self.path, mode="a", encoding="utf-8") as f:
            await f.write(line + "\n")

    async def _rewrite_array(self, data: dict):
        records = []
        if os.path.exists(self.path):
            async with aiofiles.open(self.path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                if content.strip():
                    records = json.loads(content)
        records.append(data)
        async with aiofiles.open(self.path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(records, ensure_ascii=False, indent=2))

    async def close(self):
        pass


async def read_json_lines(path: str) -> list[dict]:
    records = []
    async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
        async for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


async def read_json_array(path: str) -> list[dict]:
    async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
        content = await f.read()
    return json.loads(content) if content.strip() else []
