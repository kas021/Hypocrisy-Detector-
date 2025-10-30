"""Adapters to convert scraped items into ingestible rows."""
from __future__ import annotations

from typing import Iterable, List

from .base import ScrapedItem


def scraped_to_ingest_rows(items: Iterable[ScrapedItem]) -> List[dict]:
    rows: List[dict] = []
    for item in items:
        rows.append(
            {
                "id": item.id,
                "text": item.text,
                "title": item.title,
                "url": str(item.url),
                "source_name": item.source_name,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "author": item.author,
                "media_urls": [str(url) for url in item.media_urls],
                "raw_html": item.raw_html,
                "license": item.license,
                "extra": item.extra,
            }
        )
    return rows


__all__ = ["scraped_to_ingest_rows"]
