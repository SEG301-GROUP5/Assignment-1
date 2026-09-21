"""SQLite persistence for pages and hyperlink relationships."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class CrawlerDatabase:
    def __init__(self, path: Path, reset: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")

        if reset:
            self.conn.executescript(
                "DROP TABLE IF EXISTS pages; DROP TABLE IF EXISTS links;"
            )
            self.conn.commit()

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
                content_hash TEXT,
                depth INTEGER,
                status_code INTEGER,
                crawled_at TEXT,
                response_time REAL
            );

            CREATE INDEX IF NOT EXISTS idx_pages_content_hash
            ON pages(content_hash);

            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT,
                target_url TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_links_unique
            ON links(source_url, target_url);
            """
        )
        self.conn.commit()

    def content_hash_exists(self, content_hash: str | None) -> bool:
        """Check whether a page with this exact content was already stored,
        so near-identical pages (different URL, same content) aren't
        duplicated in the pages table."""
        if not content_hash:
            return False
        cursor = self.conn.execute(
            "SELECT 1 FROM pages WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        )
        return cursor.fetchone() is not None

    def save_page(self, record: dict) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO pages
            (url, domain, title, content, content_hash, depth, status_code, crawled_at, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["url"],
                record["domain"],
                record["title"],
                record["content"],
                record.get("content_hash"),
                record["depth"],
                record["status_code"],
                record["crawled_at"],
                record["response_time"],
            ),
        )
        self.conn.commit()

    def save_link(self, source_url: str, target_url: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO links (source_url, target_url) VALUES (?, ?)",
            (source_url, target_url),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()