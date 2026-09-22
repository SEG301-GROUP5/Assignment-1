"""SQLite persistence for pages and hyperlink relationships."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class CrawlerDatabase:
    def __init__(self, path: Path, reset: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if reset and path.exists():
            path.unlink()

        self.path = path
        self.conn = sqlite3.connect(path)

        # Safe performance tuning for larger crawl runs.
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                domain TEXT,
                title TEXT,
                content TEXT,
                depth INTEGER,
                status_code INTEGER,
                crawled_at TEXT,
                response_time REAL
            );

            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT,
                target_url TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_links_unique
            ON links(source_url, target_url);

            CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain);
            CREATE INDEX IF NOT EXISTS idx_pages_depth ON pages(depth);
            CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status_code);
            CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url);
            CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_url);
            """
        )
        self.conn.commit()

    def save_page(self, record: dict) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO pages
            (url, domain, title, content, depth, status_code, crawled_at, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["url"],
                record["domain"],
                record["title"],
                record["content"],
                record["depth"],
                record["status_code"],
                record["crawled_at"],
                record["response_time"],
            ),
        )

    def save_links(self, source_url: str, target_urls: list[str]) -> None:
        """Store all links from one page in one SQLite batch."""
        if not target_urls:
            return
        self.conn.executemany(
            "INSERT OR IGNORE INTO links (source_url, target_url) VALUES (?, ?)",
            ((source_url, target_url) for target_url in target_urls),
        )

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
