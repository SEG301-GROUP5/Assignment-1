"""Entry point for the SEG301 Focused Web Crawler assignment."""
from pathlib import Path

import config
from crawler import FocusedCrawler


def write_summary_file(summary: dict) -> None:
    output = Path(config.DATA_DIR) / "crawl_summary.txt"
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
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    crawler = FocusedCrawler()
    summary = crawler.run()
    write_summary_file(summary)
    print(f"Summary saved to: {Path(config.DATA_DIR) / 'crawl_summary.txt'}")


if __name__ == "__main__":
    main()
