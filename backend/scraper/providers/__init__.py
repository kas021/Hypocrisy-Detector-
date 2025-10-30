"""Scraper providers for government and media sources."""
from __future__ import annotations

from typing import Dict, Type

from ..base import Provider

from .govuk import GovUkProvider
from .whitehouse import WhiteHouseProvider
from .youtube import YouTubeProvider

PROVIDERS: Dict[str, Type[Provider]] = {
    GovUkProvider.slug: GovUkProvider,
    WhiteHouseProvider.slug: WhiteHouseProvider,
    YouTubeProvider.slug: YouTubeProvider,
}


__all__ = ["PROVIDERS", "GovUkProvider", "WhiteHouseProvider", "YouTubeProvider"]
