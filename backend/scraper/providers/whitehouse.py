"""Provider for White House statements and briefings."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from ..base import Provider, ScrapedItem

LOGGER = logging.getLogger(__name__)
FEED_URL = "https://www.whitehouse.gov/briefing-room/statements-releases/feed/"


class WhiteHouseProvider(Provider):
    slug = "whitehouse"

    def fetch(
        self,
        *,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Iterable[ScrapedItem]:
        try:
            response = requests.get(FEED_URL, timeout=20)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("White House feed request failed: %s", exc)
            return []

        parsed = feedparser.parse(response.text)
        items: List[ScrapedItem] = []
        for entry in parsed.entries:
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime(*entry.published_parsed[:6])
                if since and published < since:
                    continue
            content = getattr(entry, "summary", "")
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ").strip()
            if not text:
                text = getattr(entry, "title", "").strip()
            try:
                item = ScrapedItem(
                    id=getattr(entry, "id", getattr(entry, "link", "")),
                    url=getattr(entry, "link", ""),
                    title=getattr(entry, "title", "Untitled"),
                    text=text,
                    source_name="White House",
                    published_at=published,
                )
                items.append(item)
            except Exception as exc:  # pragma: no cover
                LOGGER.debug("Skipping entry due to validation error: %s", exc)
                continue
            if limit and len(items) >= limit:
                break
        return items


__all__ = ["WhiteHouseProvider"]
