import html
import json
import time
from collections import defaultdict
from urllib.parse import urlparse


class CrawlerStats:
    def __init__(self):
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.total_pages = 0
        self.successful = 0
        self.failed = 0
        self.status_codes: dict[int, int] = defaultdict(int)
        self.domain_counts: dict[str, int] = defaultdict(int)

    def start(self):
        self.start_time = time.monotonic()

    def stop(self):
        self.end_time = time.monotonic()

    def record_success(self, url: str, status_code: int):
        self.total_pages += 1
        self.successful += 1
        self.status_codes[status_code] += 1
        self.domain_counts[urlparse(url).netloc] += 1

    def record_failure(self, url: str, status_code: int | None = None):
        self.total_pages += 1
        self.failed += 1
        if status_code is not None:
            self.status_codes[status_code] += 1
        self.domain_counts[urlparse(url).netloc] += 1

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.monotonic()
        return end - self.start_time

    @property
    def pages_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self.total_pages / elapsed if elapsed > 0 else 0.0

    def top_domains(self, n: int = 5) -> list[tuple[str, int]]:
        return sorted(self.domain_counts.items(), key=lambda kv: -kv[1])[:n]

    def summary(self) -> dict:
        return {
            "total_pages": self.total_pages,
            "successful": self.successful,
            "failed": self.failed,
            "pages_per_second": self.pages_per_second,
            "elapsed_seconds": self.elapsed_seconds,
            "status_codes": dict(self.status_codes),
            "top_domains": self.top_domains(),
        }

    def export_to_json(self, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2, ensure_ascii=False)

    def export_to_html_report(self, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(_render_html_report(self.summary()))


def _render_html_report(summary: dict) -> str:
    status_rows = "".join(
        f"<tr><td>{code}</td><td>{count}</td>"
        f'<td><div class="bar" style="width:{_bar_width(count, summary["status_codes"])}%"></div></td></tr>'
        for code, count in sorted(summary["status_codes"].items())
    )
    domain_rows = "".join(
        f"<tr><td>{html.escape(domain)}</td><td>{count}</td></tr>"
        for domain, count in summary["top_domains"]
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Отчёт краулера</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  table {{ border-collapse: collapse; margin-bottom: 2rem; min-width: 320px; }}
  th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.8rem; text-align: left; }}
  .metrics {{ display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .metric {{ border: 1px solid #ccc; border-radius: 6px; padding: 0.8rem 1.2rem; }}
  .metric .value {{ font-size: 1.6rem; font-weight: 600; }}
  .bar {{ height: 10px; background: #4a7; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Отчёт краулера</h1>
<div class="metrics">
  <div class="metric"><div class="value">{summary['total_pages']}</div>страниц всего</div>
  <div class="metric"><div class="value">{summary['successful']}</div>успешно</div>
  <div class="metric"><div class="value">{summary['failed']}</div>ошибок</div>
  <div class="metric"><div class="value">{summary['pages_per_second']:.2f}</div>страниц/сек</div>
  <div class="metric"><div class="value">{summary['elapsed_seconds']:.1f}s</div>время работы</div>
</div>

<h2>Статус-коды</h2>
<table>
  <tr><th>Код</th><th>Количество</th><th></th></tr>
  {status_rows or '<tr><td colspan="3">нет данных</td></tr>'}
</table>

<h2>Топ доменов</h2>
<table>
  <tr><th>Домен</th><th>Страниц</th></tr>
  {domain_rows or '<tr><td colspan="2">нет данных</td></tr>'}
</table>
</body>
</html>
"""


def _bar_width(count: int, status_codes: dict[int, int]) -> float:
    total = sum(status_codes.values())
    return round(count / total * 100, 1) if total else 0.0
