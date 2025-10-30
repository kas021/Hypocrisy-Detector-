"""
Scraper module for contradiction-finder.

Provides pluggable providers for scraping content from various sources
while respecting robots.txt and site terms of service.
"""

from .providers import (
    Provider,
    YouTubeProvider,
    RSSProvider,
    WikipediaProvider,
    GovUkProvider,
    HansardProvider,
    GenericProvider,
)

__all__ = [
    "Provider",
    "YouTubeProvider",
    "RSSProvider",
    "WikipediaProvider",
    "GovUkProvider",
    "HansardProvider",
    "GenericProvider",
]
