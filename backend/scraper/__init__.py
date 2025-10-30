"""Scraper package for gathering hypocrisy sources."""

from .base import Provider, ScrapedItem  # noqa: F401
from .adapters import scraped_to_ingest_rows  # noqa: F401

__all__ = ["Provider", "ScrapedItem", "scraped_to_ingest_rows"]
