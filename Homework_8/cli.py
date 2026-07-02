import argparse
import asyncio
import sys

from advanced_crawler import AdvancedCrawler
from config import CrawlerConfig

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Async web crawler")
    parser.add_argument("--urls", nargs="+", help="start URLs")
    parser.add_argument("--sitemap", nargs="+", help="sitemap.xml URLs to seed from")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--max-concurrent", type=int, default=None)
    parser.add_argument("--output", default=None, help="file to save results to")
    parser.add_argument("--output-format", choices=["jsonl", "json_array", "csv", "sqlite"], default=None)
    parser.add_argument("--config", default=None, help="path to a JSON or YAML config file")
    parser.add_argument("--respect-robots", dest="respect_robots", action="store_true", default=None)
    parser.add_argument("--no-respect-robots", dest="respect_robots", action="store_false")
    parser.add_argument("--rate-limit", type=float, default=None, help="requests per second")
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--log-level", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--report", default=None, help="write an HTML report to this path")
    return parser


def build_config(args: argparse.Namespace) -> CrawlerConfig:
    config = CrawlerConfig.from_file(args.config) if args.config else CrawlerConfig()

    if args.urls:
        config.start_urls = args.urls
    if args.sitemap:
        config.sitemap_urls = args.sitemap
    if args.max_pages is not None:
        config.max_pages = args.max_pages
    if args.max_depth is not None:
        config.max_depth = args.max_depth
    if args.max_concurrent is not None:
        config.max_concurrent = args.max_concurrent
    if args.output is not None:
        config.output = args.output
    if args.output_format is not None:
        config.output_format = args.output_format
    if args.respect_robots is not None:
        config.respect_robots = args.respect_robots
    if args.rate_limit is not None:
        config.requests_per_second = args.rate_limit
    if args.log_file is not None:
        config.log_file = args.log_file
    if args.log_level is not None:
        config.log_level = args.log_level

    return config


async def async_main(argv: list[str] | None = None) -> dict:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.config and not args.urls and not args.sitemap:
        parser.error("either --config or --urls/--sitemap is required")

    config = build_config(args)

    async with AdvancedCrawler(config) as crawler:
        results = await crawler.crawl()
        stats = crawler.get_stats()

        print(f"Обработано: {stats['total_pages']} страниц")
        print(f"Успешно: {stats['successful']}")
        print(f"Ошибок: {stats['failed']}")
        print(f"Скорость: {stats['pages_per_second']:.2f} стр/сек")

        if args.report:
            crawler.export_to_html_report(args.report)
            print(f"HTML-отчёт сохранён: {args.report}")

    return results


def main(argv: list[str] | None = None):
    asyncio.run(async_main(argv))


if __name__ == "__main__":
    main()
