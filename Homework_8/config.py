import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class CrawlerConfig:
    start_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    max_pages: int = 100
    max_depth: int = 2
    max_concurrent: int = 10
    requests_per_second: float = 1.0
    respect_robots: bool = True
    same_domain_only: bool = False
    exclude_patterns: list[str] = field(default_factory=list)
    include_patterns: list[str] = field(default_factory=list)
    output: str = "results.jsonl"
    output_format: str = "jsonl"  # jsonl | json_array | csv | sqlite
    log_file: str | None = "crawler.log"
    log_level: str = "INFO"
    user_agent: str = "AsyncCrawlerBot/1.0"

    @classmethod
    def from_file(cls, path: str) -> "CrawlerConfig":
        text = Path(path).read_text(encoding="utf-8")
        if path.endswith((".yaml", ".yml")):
            if yaml is None:
                raise RuntimeError("pyyaml is not installed; install it or use a .json config file")
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text) if text.strip() else {}

        known_fields = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known_fields
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")

        return cls(**data)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
