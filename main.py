"""Điểm khởi chạy cho bài tập SEG301 Focused Web Crawler."""
from pathlib import Path

import config
from crawler import FocusedCrawler


README_RESULTS_START = "<!-- AUTO_CRAWL_RESULTS_START -->"
README_RESULTS_END = "<!-- AUTO_CRAWL_RESULTS_END -->"


def summary_lines(summary: dict) -> list[str]:
    lines = [
        "=" * 46,
        " TÓM TẮT KẾT QUẢ CRAWL",
        "=" * 46,
        f"Chủ đề                 : {summary['topic']}",
        f"Số Seed URL            : {summary['seed_urls']}",
        f"Số trang đã crawl      : {summary['pages_crawled']}",
        f"Số trang HTML đã lưu   : {summary['html_pages_stored']}",
        f"URL duy nhất phát hiện : {summary['unique_urls_discovered']}",
        f"URL đã bỏ qua          : {summary['skipped_urls']}",
        f"Request thất bại       : {summary['failed_requests']}",
        f"Redirect đã đi theo    : {summary['redirects_followed']}",
        f"Độ sâu tối đa          : {summary['maximum_depth']}",
    ]
    for depth in range(summary["maximum_depth"] + 1):
        lines.append(f"Depth {depth:<2}                : {summary['depth_counts'].get(depth, 0)}")
    for status, count in summary["status_counts"].items():
        lines.append(f"HTTP {status:<3}               : {count}")
    for status, count in summary["redirect_status_counts"].items():
        lines.append(f"Redirect HTTP {status:<3}      : {count} lần")
    lines.extend(
        [
            f"Tổng link đã trích xuất: {summary['total_links_extracted']}",
            f"Tổng link vào Frontier : {summary['total_links_queued']}",
            f"Text đã lưu            : {summary['total_content_chars']:,} ký tự",
            f"Frontier còn lại       : {summary['frontier_remaining']}",
            "=" * 46,
        ]
    )
    return lines


def write_summary_file(summary: dict) -> Path:
    output = Path(config.DATA_DIR) / "crawl_summary.txt"
    output.write_text("\n".join(summary_lines(summary)) + "\n", encoding="utf-8")
    return output


def update_readme_results(summary: dict) -> bool:
    """Tự động chèn thống kê crawl thật vào README.md sau mỗi lần chạy."""
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

    print(f"Đã lưu thống kê tại: {summary_path}")
    if readme_updated:
        print("Đã tự động cập nhật thống kê crawl cuối cùng vào README.md.")
    else:
        print("CẢNH BÁO: Không tìm thấy marker tự động trong README.md nên README chưa được cập nhật.")


if __name__ == "__main__":
    main()
