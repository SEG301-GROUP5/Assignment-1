"""Configuration for the SEG301 Focused Web Crawler assignment.
"""
from pathlib import Path

TOPIC = "Education"

SEED_URLS = [
    "https://ocw.mit.edu/",
]

ALLOWED_DOMAINS = [
    "ocw.mit.edu",
]

# Kept for compatibility with main.py's --seed/--tag flags (optional here
# since SEED_URLS already has only one entry). Not required for normal use.
SEED_OWNERS = {
    1: "ngan",
}

MAX_DEPTH = 3
MAX_PAGES = 100
REQUEST_TIMEOUT = 10
CRAWL_DELAY = 1.0

# The crawler reads robots.txt dynamically before crawling each host.
RESPECT_ROBOTS_TXT = True
ROBOTS_FAIL_CLOSED = True

USER_AGENT = "SEG301-FocusedCrawler/1.0 (+educational-assignment)"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "crawler.db"

# Rebuild the database on each run so the summary and DB describe one clean run.
RESET_DATABASE_ON_START = True

# Non-HTML resources that should normally not be crawled.
BLOCKED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".wav", ".mp4", ".avi", ".mov", ".wmv", ".webm",
    ".xml", ".rss", ".atom",
}
MAX_PAGES = 100
REQUEST_TIMEOUT = 10
CRAWL_DELAY = 1.0

# The crawler reads robots.txt dynamically before crawling each host.
RESPECT_ROBOTS_TXT = True
ROBOTS_FAIL_CLOSED = True

USER_AGENT = "SEG301-FocusedCrawler/1.0 (+educational-assignment)"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "crawler.db"

# Rebuild the database on each run so the summary and DB describe one clean run.
RESET_DATABASE_ON_START = True

# Non-HTML resources that should normally not be crawled.
BLOCKED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".wav", ".mp4", ".avi", ".mov", ".wmv", ".webm",
    ".xml", ".rss", ".atom",
}
