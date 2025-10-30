"""Hypocrisy detection by comparing statements against the corpus."""
from __future__ import annotations

import json
import math
from typing import List

try:  # pragma: no cover - optional dependency for tests
    import numpy as np
except Exception:  # pragma: no cover - fallback
    np = None  # type: ignore


from sentence_transformers import SentenceTransformer

from .db import CorpusDatabase
from .nli import NLIScorer
from .schemas import HypocrisyHit

_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class HypocrisyDetector:
    def __init__(self, scorer: NLIScorer | None = None) -> None:
        self.db = CorpusDatabase()
        self.scorer = scorer or NLIScorer()
        self.embedder = SentenceTransformer(_EMBED_MODEL)

    def _candidate_segments(self, text: str, limit: int = 25):
        segments = self.db.fetch_segments_with_embeddings()
        if not segments:
            return []
        query_vec = self.embedder.encode([text])[0]
        query_norm = _norm(query_vec) or 1.0
        results = []
        for segment, vector in segments:
            denom = (_norm(vector) or 1.0) * query_norm
            similarity = float(_dot(query_vec, vector) / denom)

            results.append((segment, similarity))
        results.sort(key=lambda item: item[1], reverse=True)
        return [segment for segment, _ in results[:limit]]

    def check(self, statement: str, top_k: int = 5) -> List[HypocrisyHit]:
        candidates = self._candidate_segments(statement)
        if not candidates:
            return []
        scores = self.scorer.score_batch(
            [(segment.text, statement) for segment in candidates]
        )
        ranked = sorted(zip(candidates, scores), key=lambda item: item[1], reverse=True)[
            :top_k
        ]
        hits: List[HypocrisyHit] = []
        for segment, score in ranked:
            source = self.db.fetch_source(segment.source_id)
            extra = {}
            if source and source.get("extra_json"):
                try:
                    extra = json.loads(source["extra_json"])
                except Exception:  # pragma: no cover - defensive parsing
                    extra = {}

            hits.append(
                HypocrisyHit(
                    score=float(score),
                    corpus_text=segment.text,
                    source_type=source.get("source_type", "unknown") if source else "unknown",
                    source_title=source.get("title", "Unknown") if source else "Unknown",
                    url_or_path=source.get("url_or_path", "") if source else "",
                    ts_start=segment.ts_start,
                    ts_end=segment.ts_end,
                    extra=extra,

                )
            )
        return hits


def _norm(vector) -> float:
    if np is not None:
        return float(np.linalg.norm(vector))
    return math.sqrt(sum(float(x) * float(x) for x in vector))


def _dot(a, b) -> float:
    if np is not None:
        return float(np.dot(a, b))
    return float(sum(float(x) * float(y) for x, y in zip(a, b)))



__all__ = ["HypocrisyDetector"]
