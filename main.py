"""Entry point for the SEG301 Focused Web Crawler assignment.
"""
import argparse
import sys

# Windows consoles often default to the cp1252 code page, which cannot
# encode every Unicode character a crawled page's title may contain
# (e.g. Turkish "İleri Çalışmalar"). Force UTF-8 output with a safe
# fallback so an unusual character never crashes a long crawl run.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import config
from crawler import FocusedCrawler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SEG301 Focused Web Crawler - personal copy (seed #1)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help=(
            "1-based index into config.SEED_URLS (there are "
            f"{len(config.SEED_URLS)} seed(s) in this personal copy)."
        ),
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help=(
            "Label used in output file names: data/crawler_<tag>.db and "
            "data/crawl_summary_<tag>.txt. Defaults to the member name in "
            "config.SEED_OWNERS for the chosen --seed, or 'ngan' when "
            "--seed is omitted."
        ),
    )
    return parser.parse_args()


def resolve_run(args: argparse.Namespace):
    """Work out which seed URL(s) to crawl and what to name the output files.

    This is Ngân's personal copy: config.SEED_URLS already has only her one
    assigned seed, so plain `python main.py` (no --seed needed) is enough.
    """
    if args.seed is None:
        return list(config.SEED_URLS), (args.tag or "ngan")

    index = args.seed - 1
    if index < 0 or index >= len(config.SEED_URLS):
        raise SystemExit(
            f"--seed must be between 1 and {len(config.SEED_URLS)} "
            f"(config.SEED_URLS has {len(config.SEED_URLS)} entries)."
        )

    seed_urls = [config.SEED_URLS[index]]
    default_tag = config.SEED_OWNERS.get(args.seed, f"seed{args.seed}")
    return seed_urls, (args.tag or default_tag)


def write_summary_file(summary: dict, path: Path) -> None:
    lines = [
        "=" * 46,
        " CRAWLING SUMMARY",
        "=" * 46,
        f"Topic                  : {summary['topic']}",
        f"Seed URLs              : {summary['seed_urls']}",
        f"Pages Crawled          : {summary['pages_crawled']}",
        f"Unique URLs Discovered : {summary['unique_urls_discovered']}",
        f"Skipped URLs           : {summary['skipped_urls']}",
        f"Failed Requests        : {summary['failed_requests']}",
        f"Maximum Depth          : {summary['maximum_depth']}",
    ]
    for depth, count in summary["depth_counts"].items():
        lines.append(f"Depth {depth:<2}                : {count}")
    for status, count in summary["status_counts"].items():
        lines.append(f"HTTP {status:<3}               : {count}")
    lines.append(f"Frontier Remaining     : {summary['frontier_remaining']}")
    lines.append("=" * 46)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    seed_urls, tag = resolve_run(args)

    db_path = Path(config.DATA_DIR) / f"crawler_{tag}.db"
    summary_path = Path(config.DATA_DIR) / f"crawl_summary_{tag}.txt"

    crawler = FocusedCrawler(seed_urls=seed_urls, database_path=db_path)
    summary = crawler.run()
    write_summary_file(summary, summary_path)

    print(f"Database saved to : {db_path}")
    print(f"Summary saved to  : {summary_path}")


if __name__ == "__main__":
    main()