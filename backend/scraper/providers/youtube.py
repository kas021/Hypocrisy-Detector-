"""YouTube provider using yt-dlp to gather transcripts or descriptions."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from ..base import Provider, ScrapedItem

LOGGER = logging.getLogger(__name__)
CHANNELS_FILE = Path(__file__).with_name("youtube_channels.yaml")

try:  # pragma: no cover - optional dependency
    import yt_dlp
except Exception:  # pragma: no cover - gracefully degrade
    yt_dlp = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - fallback parser
    yaml = None  # type: ignore


def _parse_upload_date(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return None


def _load_channels() -> List[str]:
    env_value = os.getenv("YOUTUBE_CHANNELS")
    if env_value:
        return [item.strip() for item in env_value.split(",") if item.strip()]
    if CHANNELS_FILE.exists():
        data = CHANNELS_FILE.read_text(encoding="utf-8")
        if yaml:
            try:
                parsed = yaml.safe_load(data)
                if isinstance(parsed, dict):
                    if "channels" in parsed and isinstance(parsed["channels"], list):
                        return [str(item) for item in parsed["channels"] if str(item).strip()]
                elif isinstance(parsed, list):
                    return [str(item) for item in parsed if str(item).strip()]
            except Exception as exc:
                LOGGER.warning("Unable to parse %s: %s", CHANNELS_FILE, exc)
        # fallback: treat as newline separated list ignoring comments
        channels: List[str] = []
        for line in data.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-"):
                line = line.lstrip("- ")
            channels.append(line)
        if channels:
            return channels
    return []


class YouTubeProvider(Provider):
    slug = "youtube"

    def fetch(
        self,
        *,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Iterable[ScrapedItem]:
        if yt_dlp is None:
            LOGGER.warning("yt-dlp not available - skipping YouTube provider")
            return []
        channels = _load_channels()
        if not channels:
            LOGGER.info("No YouTube channels configured; skipping")
            return []

        items: List[ScrapedItem] = []
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "extract_flat": "in_playlist",
        }
        for channel in channels:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(channel, download=False)
            except Exception as exc:  # pragma: no cover - network dependent
                LOGGER.warning("Failed to fetch channel %s: %s", channel, exc)
                continue
            entries = info.get("entries") or []
            for entry in entries:
                upload_date = _parse_upload_date(entry.get("upload_date"))
                if since and upload_date and upload_date < since:
                    continue
                text = entry.get("description") or entry.get("title") or ""
                video_url = entry.get("url") or entry.get("webpage_url")
                if not video_url:
                    continue
                try:
                    item = ScrapedItem(
                        id=entry.get("id") or video_url,
                        url=video_url,
                        title=entry.get("title") or "Untitled",
                        text=text.strip(),
                        source_name=entry.get("channel") or "YouTube",
                        published_at=upload_date,
                        extra={"channel_url": channel},
                    )
                    items.append(item)
                except Exception as exc:  # pragma: no cover
                    LOGGER.debug("Skipping video due to validation error: %s", exc)
                    continue
                if limit and len(items) >= limit:
                    return items
        return items


__all__ = ["YouTubeProvider"]
