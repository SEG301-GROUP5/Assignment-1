"""Configuration for the SEG301 Focused Web Crawler assignment."""
from pathlib import Path

TOPIC = "Education"

# One-link version requested by the group.
# The crawler starts ONLY from this Stanford Engineering page.
SEED_URLS = [
    "https://engineering.stanford.edu/students-academics/academics/online-learning",
]

# Keep the crawl focused on Stanford Engineering only.
# Links to www.stanford.edu, online.stanford.edu, external departments, social media,
# PDFs, etc. may still be stored in the links table, but they are not crawled.
ALLOWED_DOMAINS = [
    "engineering.stanford.edu",
]

# Full-data-oriented limits. BFS still stops safely at these boundaries.
MAX_DEPTH = 4
MAX_PAGES = 1500
REQUEST_TIMEOUT = 15
CRAWL_DELAY = 1.0
MAX_REDIRECTS = 5

# The crawler reads robots.txt dynamically before crawling the host.
RESPECT_ROBOTS_TXT = True
ROBOTS_FAIL_CLOSED = True

USER_AGENT = "SEG301-FocusedCrawler/1.0 (+educational-assignment)"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "crawler.db"

# Rebuild the database on each run so DB + summary describe one clean run.
RESET_DATABASE_ON_START = True

# Non-HTML resources that should normally not be crawled.
BLOCKED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".wav", ".mp4", ".avi", ".mov", ".wmv", ".webm",
    ".xml", ".rss", ".atom",
}
