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
        self.conn.execute("PRAGMA foreign_keys = ON")
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
        self.conn.commit()

    def save_link(self, source_url: str, target_url: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO links (source_url, target_url) VALUES (?, ?)",
            (source_url, target_url),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
