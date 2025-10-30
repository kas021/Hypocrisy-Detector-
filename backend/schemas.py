"""Shared dataclasses and models for backend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Source:
    id: int
    title: str
    source_type: str
    url_or_path: str


@dataclass
class Segment:
    id: int
    source_id: int
    text: str
    ts_start: Optional[float]
    ts_end: Optional[float]


@dataclass
class HypocrisyHit:
    score: float
    corpus_text: str
    source_type: str
    source_title: str
    url_or_path: str
    ts_start: Optional[float]
    ts_end: Optional[float]


__all__ = ["Source", "Segment", "HypocrisyHit"]
