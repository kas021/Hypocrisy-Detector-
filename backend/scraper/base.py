"""Base classes and models for scraper providers."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

try:  # pragma: no cover - fallback for environments without pydantic
    from pydantic import BaseModel, Field, HttpUrl
except Exception:  # pragma: no cover
    class _FieldDefault:
        def __init__(self, default=None, default_factory=None):
            self.default = default
            self.default_factory = default_factory

        def get(self):
            if self.default_factory is not None:
                return self.default_factory()
            return self.default

    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for key, value in self.__class__.__dict__.items():
                if isinstance(value, _FieldDefault):
                    setattr(self, key, value.get())
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self):
            return self.__dict__.copy()

    def Field(default=None, default_factory=None):  # type: ignore
        return _FieldDefault(default=default, default_factory=default_factory)

    HttpUrl = str  # type: ignore


class ScrapedItem(BaseModel):
    id: str
    url: HttpUrl
    title: str
    text: str
    source_name: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    media_urls: List[HttpUrl] = Field(default_factory=list)
    raw_html: Optional[str] = None
    license: Optional[str] = None
    extra: Dict = Field(default_factory=dict)


class Provider:
    slug: str

    def fetch(
        self,
        *,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Iterable[ScrapedItem]:
        raise NotImplementedError


__all__ = ["ScrapedItem", "Provider"]
