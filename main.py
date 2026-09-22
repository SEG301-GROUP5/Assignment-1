"""Entry point for the SEG301 Focused Web Crawler assignment."""
from pathlib import Path

import config
from crawler import FocusedCrawler


README_RESULTS_START = "<!-- AUTO_CRAWL_RESULTS_START -->"
README_RESULTS_END = "<!-- AUTO_CRAWL_RESULTS_END -->"


def summary_lines(summary: dict) -> list[str]:
    lines = [
        "=" * 46,
        " CRAWLING SUMMARY",
        "=" * 46,
        f"Topic                  : {summary['topic']}",
        f"Seed URLs              : {summary['seed_urls']}",
        f"Pages Crawled          : {summary['pages_crawled']}",
        f"HTML Pages Stored      : {summary['html_pages_stored']}",
        f"Unique URLs Discovered : {summary['unique_urls_discovered']}",
        f"Skipped URLs           : {summary['skipped_urls']}",
        f"Failed Requests        : {summary['failed_requests']}",
        f"Redirects Followed     : {summary['redirects_followed']}",
        f"Maximum Depth          : {summary['maximum_depth']}",
    ]
    for depth in range(summary["maximum_depth"] + 1):
        lines.append(f"Depth {depth:<2}                : {summary['depth_counts'].get(depth, 0)}")
    for status, count in summary["status_counts"].items():
        lines.append(f"HTTP {status:<3}               : {count}")
    for status, count in summary["redirect_status_counts"].items():
        lines.append(f"Redirect HTTP {status:<3}      : {count} hop(s)")
    lines.extend(
        [
            f"Links Extracted        : {summary['total_links_extracted']}",
            f"Links Queued           : {summary['total_links_queued']}",
            f"Visible Text Stored    : {summary['total_content_chars']:,} chars",
            f"Frontier Remaining     : {summary['frontier_remaining']}",
            "=" * 46,
        ]
    )
    return lines


def write_summary_file(summary: dict) -> Path:
    output = Path(config.DATA_DIR) / "crawl_summary.txt"
    output.write_text("\n".join(summary_lines(summary)) + "\n", encoding="utf-8")
    return output


def update_readme_results(summary: dict) -> bool:
    """Insert the real final crawl statistics into README.md after every run."""
    readme = Path(config.BASE_DIR) / "README.md"
    if not readme.exists():
        return False

    text = readme.read_text(encoding="utf-8")
    if README_RESULTS_START not in text or README_RESULTS_END not in text:
        return False

    before, remainder = text.split(README_RESULTS_START, 1)
    _, after = remainder.split(README_RESULTS_END, 1)

    auto_block = (
        README_RESULTS_START
        + "\n\n```text\n"
        + "\n".join(summary_lines(summary))
        + "\n```\n\n"
        + README_RESULTS_END
    )
    readme.write_text(before + auto_block + after, encoding="utf-8")
    return True


def main() -> None:
    crawler = FocusedCrawler()
    summary = crawler.run()
    summary_path = write_summary_file(summary)
    readme_updated = update_readme_results(summary)

    print(f"Summary saved to: {summary_path}")
    if readme_updated:
        print("README.md final crawling statistics updated automatically.")
    else:
        print("WARNING: README.md auto-results markers were not found; README was not updated.")


if __name__ == "__main__":
    main()
