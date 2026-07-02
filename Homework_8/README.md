# Async Crawler

Асинхронный веб-краулер на aiohttp: параллельная загрузка, парсинг HTML, приоритетная
очередь с ограничением глубины, rate limiting и robots.txt, классификация ошибок с
повторами и circuit breaker, сохранение в JSON/CSV/SQLite, sitemap.xml как источник
стартовых URL, статистика и HTML-отчёт, CLI.

## Установка

```bash
pip install -r requirements.txt
```

## Быстрый старт (CLI)

```bash
python cli.py --urls https://example.com --max-pages 20 --output results.jsonl --report report.html
```

Через конфиг:

```bash
python cli.py --config config.example.json
```

Параметры CLI переопределяют значения из `--config`, если заданы одновременно.

### Параметры CLI

| Флаг | Назначение |
|---|---|
| `--urls` | стартовые URL (можно несколько) |
| `--sitemap` | URL sitemap.xml, из которого извлекаются стартовые URL |
| `--max-pages` | лимит страниц за обход |
| `--max-depth` | глубина обхода от стартовых URL |
| `--max-concurrent` | конкурентность (глобальный семафор) |
| `--rate-limit` | запросов в секунду (на домен) |
| `--respect-robots` / `--no-respect-robots` | соблюдать robots.txt |
| `--output` / `--output-format` | файл результатов и формат (`jsonl`, `json_array`, `csv`, `sqlite`) |
| `--config` | путь к JSON/YAML конфигу |
| `--log-file` / `--log-level` | логирование в файл (с ротацией) и уровень |
| `--report` | путь для HTML-отчёта по завершении |

## Программное использование

```python
import asyncio
from advanced_crawler import AdvancedCrawler

async def main():
    async with AdvancedCrawler.from_config("config.example.json") as crawler:
        await crawler.crawl()
        stats = crawler.get_stats()
        print(f"Обработано: {stats['total_pages']} страниц")
        crawler.export_to_html_report("report.html")

asyncio.run(main())
```

## Модули

| Файл | Назначение |
|---|---|
| `crawler.py` | `AsyncCrawler` — базовый асинхронный краулер (fetch, parse, crawl) |
| `html_parser.py` | извлечение ссылок, заголовков, изображений, таблиц, метаданных |
| `crawler_queue.py` | приоритетная очередь URL с учётом глубины |
| `semaphore_manager.py` | глобальный + per-domain семафоры конкурентности |
| `rate_limiter.py` | ограничение скорости запросов, per-domain/глобально |
| `robots_parser.py` | загрузка и соблюдение robots.txt |
| `errors.py` | иерархия ошибок (Transient/Permanent/Network/Parse) |
| `retry_strategy.py`, `retry_stats.py` | повторы с экспоненциальным backoff и статистикой |
| `circuit_breaker.py` | временная блокировка проблемного домена |
| `data_storage.py`, `csv_storage.py`, `sqlite_storage.py` | сохранение результатов |
| `sitemap_parser.py` | загрузка sitemap.xml / sitemap index как источника URL |
| `crawler_stats.py` | агрегированная статистика, экспорт в JSON/HTML |
| `config.py` | конфигурация из JSON/YAML |
| `logging_setup.py` | логирование в файл (с ротацией) и консоль |
| `advanced_crawler.py` | `AdvancedCrawler` — интеграция всех компонентов |
| `cli.py` | командная строка |

## Формат конфигурации

См. `config.example.json`. Поддерживаются JSON и YAML (требует `pyyaml`). Неизвестные
ключи в конфиге считаются ошибкой (опечатка в имени поля не проходит молча).

## Формат сохраняемой записи

```json
{
  "url": "https://example.com/page",
  "requested_url": "https://example.com/original-link",
  "title": "...",
  "text": "...",
  "links": ["..."],
  "metadata": {"description": "...", "keywords": "..."},
  "crawled_at": "2026-01-01T00:00:00+00:00",
  "status_code": 200,
  "content_type": "text/html"
}
```

`url` — итоговый адрес после разрешённых редиректов, `requested_url` — исходно
запрошенный. Оба сохраняются, поскольку при редиректе на другой домен запрос к нему
заново проходит проверку robots.txt и rate limit (см. ниже).

## Безопасность

- Редиректы обрабатываются вручную (`allow_redirects=False`): каждый хоп заново
  проверяется через robots.txt, rate limiter и circuit breaker для своего домена —
  иначе редирект на другой домен обошёл бы политику этого домена.
- robots.txt и sitemap.xml не следуют за редиректами при загрузке — иначе можно было бы
  подменить политику одного домена содержимым другого.
- sitemap.xml парсится через `defusedxml`, отклоняет DTD/внешние сущности (XXE, billion
  laughs), ограничен по размеру и глубине рекурсии.
- Значения, попадающие в CSV, экранируются от formula injection (`=`, `+`, `-`, `@` в
  начале ячейки).

## Тесты

```bash
pytest
```

87 тестов покрывают все модули, включая интеграционные сценарии (крауленг с
sitemap-сидированием, сохранение в три формата хранения одновременно, обход редиректов).

## Что не реализовано

Прокси, cookies/сессии, JS-рендеринг и распределённый краулинг (пункт 12,
опциональный) не реализованы — вне текущего объёма задания.
