"""Configuration for the SEG301 Focused Web Crawler assignment."""
from pathlib import Path

TOPIC = "Education"

# The lecturer allows up to 4 domains. This project uses 5 starting web pages
# (seed URLs) across 2 Education domains so it stays within that requirement.
SEED_URLS = [
    "https://www.stanford.edu/academics/everyone"
]

# Root-domain form is intentional. Subdomains such as www.stanford.edu and
# engineering.stanford.edu are accepted by parser.domain_is_allowed().
ALLOWED_DOMAINS = [
    "stanford.edu",
]

MAX_DEPTH = 3
MAX_PAGES = 100
REQUEST_TIMEOUT = 10
CRAWL_DELAY = 1.0
MAX_REDIRECTS = 5

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
