"""Crawler configuration - member H branch.

Seed: https://ocw.mit.edu/search/
Depth bắt đầu từ 1 (không dùng depth 0).
"""
from pathlib import Path

# ==== Định danh ====
TOPIC = "Education"
MEMBER = "h"
 
# ==== Đường dẫn (bắt buộc cho main.py + crawler.py) ====
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "crawler_h.db"   # DB riêng để không conflict khi merge
RESET_DATABASE_ON_START = False             # True = xoá DB cũ mỗi lần chạy

# ==== SEED: CHỈ 1 seed của thành viên h ====
SEED_URLS = [
    "https://ocw.mit.edu/search/",
]

# Depth bắt đầu — code crawler.py dùng 0 cứng, ta sẽ patch riêng (xem phần dưới)
START_DEPTH = 1

# ==== Domain cho phép ====
ALLOWED_DOMAINS = [
    "ocw.mit.edu",
    "www.ocw.mit.edu",
]

# ==== Giới hạn crawl ====
MAX_PAGES = 150
MAX_DEPTH = 3               # depth 1 -> 2 -> 3
REQUEST_TIMEOUT = 10
CRAWL_DELAY = 1.0

# ==== Robots ====
RESPECT_ROBOTS_TXT = True
ROBOTS_FAIL_CLOSED = False   # robots.txt lỗi -> vẫn cho crawl
MAX_REDIRECTS = 5

# ==== User-Agent ====
USER_AGENT = (
    "SEG301-CourseCrawler/1.0 "
    "(student project; member h; contact: h@example.edu)"
)

# ==== File bị chặn ====
BLOCKED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".exe", ".dmg", ".apk",
}