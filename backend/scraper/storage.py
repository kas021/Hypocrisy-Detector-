"""SQLite storage helpers for scraped raw items."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Iterable, Tuple

from .base import ScrapedItem


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_items (
    url TEXT PRIMARY KEY,
    item_id TEXT,
    title TEXT,
    text TEXT,
    source_name TEXT,
    published_at TEXT,
    author TEXT,
    media_urls_json TEXT,
    raw_html TEXT,
    license TEXT,
    extra_json TEXT,
    fetched_at TEXT
);
"""


class RawItemStore:
    """Lightweight wrapper around SQLite for scraped items."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute(_SCHEMA_SQL)
        self.conn.commit()

    def upsert_items(self, items: Iterable[ScrapedItem]) -> Tuple[int, int]:
        inserted = 0
        updated = 0
        for item in items:
            payload = {
                "url": str(item.url),
                "item_id": item.id,
                "title": item.title,
                "text": item.text,
                "source_name": item.source_name,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "author": item.author,
                "media_urls_json": json.dumps([str(url) for url in item.media_urls]),
                "raw_html": item.raw_html,
                "license": item.license,
                "extra_json": json.dumps(item.extra or {}),
                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            existing = self.conn.execute(
                "SELECT url FROM raw_items WHERE url = ?", (payload["url"],)
            ).fetchone()
            if existing:
                self.conn.execute(
                    """
                    UPDATE raw_items
                    SET item_id = :item_id,
                        title = :title,
                        text = :text,
                        source_name = :source_name,
                        published_at = :published_at,
                        author = :author,
                        media_urls_json = :media_urls_json,
                        raw_html = :raw_html,
                        license = :license,
                        extra_json = :extra_json,
                        fetched_at = :fetched_at
                    WHERE url = :url
                    """,
                    payload,
                )
                updated += 1
            else:
                self.conn.execute(
                    """
                    INSERT INTO raw_items (
                        url, item_id, title, text, source_name, published_at, author,
                        media_urls_json, raw_html, license, extra_json, fetched_at
                    ) VALUES (:url, :item_id, :title, :text, :source_name, :published_at, :author,
                              :media_urls_json, :raw_html, :license, :extra_json, :fetched_at)
                    """,
                    payload,
                )
                inserted += 1
        self.conn.commit()
        return inserted, updated

    def all_items(self) -> Iterable[ScrapedItem]:
        rows = self.conn.execute("SELECT * FROM raw_items ORDER BY fetched_at DESC")
        for row in rows:
            yield ScrapedItem(
                id=row["item_id"] or row["url"],
                url=row["url"],
                title=row["title"],
                text=row["text"],
                source_name=row["source_name"],
                published_at=dt.datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
                author=row["author"],
                media_urls=json.loads(row["media_urls_json"] or "[]"),
                raw_html=row["raw_html"],
                license=row["license"],
                extra=json.loads(row["extra_json"] or "{}"),
            )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "RawItemStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["RawItemStore"]
