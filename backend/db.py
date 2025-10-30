"""SQLite helpers for storing transcripts and embeddings."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

try:  # pragma: no cover - optional dependency for tests
    import numpy as np
except Exception:  # pragma: no cover - fallback path
    np = None  # type: ignore

from sqlite_utils import Database as SQLiteDatabase

from .config import REPO_ROOT, ensure_dirs
from .schemas import Segment


class CorpusDatabase:
    def __init__(self) -> None:
        config = ensure_dirs()
        data_dir = REPO_ROOT / config["DATA_DIR"]
        self.db_path = data_dir / "db" / "corpus.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = SQLiteDatabase(self.db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        sources = self.db.table("sources")
        sources.create(
            {
                "id": int,
                "title": str,
                "source_type": str,
                "url_or_path": str,
                "published_at": str,
                "author": str,
                "extra_json": str,
            },
            pk="id",
            if_not_exists=True,
        )
        sources.create_index(["url_or_path"], if_not_exists=True, unique=True)
        segments = self.db.table("segments")
        segments.create(
            {
                "id": int,
                "source_id": int,
                "text": str,
                "ts_start": float,
                "ts_end": float,
                "doc_id": str,
            },
            pk="id",
            if_not_exists=True,
        )
        segments.create_index(["doc_id"], if_not_exists=True)
        embeddings = self.db.table("embeddings")
        embeddings.create(
            {
                "segment_id": int,
                "vector": str,
            },
            pk="segment_id",
            if_not_exists=True,
        )

        # ensure optional columns exist when upgrading older databases
        existing_cols = sources.columns_dict
        if "published_at" not in existing_cols:
            sources.add_column("published_at", str, default=None)
        if "author" not in existing_cols:
            sources.add_column("author", str, default=None)
        if "extra_json" not in existing_cols:
            sources.add_column("extra_json", str, default="{}")

        segment_cols = segments.columns_dict
        if "doc_id" not in segment_cols:
            segments.add_column("doc_id", str, default=None)

    def add_source(
        self,
        title: str,
        source_type: str,
        url_or_path: str,
        *,
        published_at: Optional[datetime] = None,
        author: Optional[str] = None,
        extra: Optional[Dict] = None,
    ) -> int:
        table = self.db.table("sources")
        existing = list(table.rows_where("url_or_path = ?", [url_or_path], limit=1))
        payload = {
            "title": title,
            "source_type": source_type,
            "url_or_path": url_or_path,
            "published_at": published_at.isoformat() if published_at else None,
            "author": author,
            "extra_json": json.dumps(extra or {}),
        }
        if existing:
            source_id = existing[0]["id"]
            table.update(source_id, payload)
            return int(source_id)

        source_id = table.insert(payload, pk="id")
        return int(source_id)

    def add_segment(
        self,
        source_id: int,
        text: str,
        ts_start: Optional[float],
        ts_end: Optional[float],
        embedding: Iterable[float],
        *,
        doc_id: Optional[str] = None,
    ) -> int:
        seg_table = self.db.table("segments")
        seg_id = seg_table.insert(
            {
                "source_id": source_id,
                "text": text,
                "ts_start": ts_start,
                "ts_end": ts_end,
                "doc_id": doc_id,
            },
            pk="id",
        )
        emb_table = self.db.table("embeddings")
        emb_table.upsert(
            {
                "segment_id": int(seg_id),
                "vector": json.dumps(list(embedding)),
            },
            pk="segment_id",
        )
        return int(seg_id)

    def fetch_segments_with_embeddings(self) -> List[Tuple[Segment, np.ndarray]]:
        segments = []
        seg_table = self.db.table("segments")
        emb_table = self.db.table("embeddings")
        for row in seg_table.rows:
            try:
                emb_row = emb_table.get(row["id"])
                raw_vector = json.loads(emb_row["vector"])
                if np is not None:
                    vector = np.array(raw_vector, dtype="float32")
                else:
                    vector = [float(x) for x in raw_vector]
            except KeyError:
                if np is not None:
                    vector = np.zeros(384, dtype="float32")
                else:
                    vector = [0.0] * 384
            segments.append(
                (
                    Segment(
                        id=row["id"],
                        source_id=row["source_id"],
                        text=row["text"],
                        ts_start=row.get("ts_start"),
                        ts_end=row.get("ts_end"),
                    ),
                    vector,
                )
            )
        return segments

    def fetch_source(self, source_id: int):
        table = self.db.table("sources")
        try:
            return table.get(source_id)
        except KeyError:
            return {}

    def search_segments(self, query: str, limit: int = 10) -> List[Segment]:
        seg_table = self.db.table("segments")
        pattern = f"%{query}%"
        rows = seg_table.rows_where("text LIKE ?", [pattern], limit=limit)
        return [
            Segment(
                id=row["id"],
                source_id=row["source_id"],
                text=row["text"],
                ts_start=row.get("ts_start"),
                ts_end=row.get("ts_end"),
            )
            for row in rows
        ]


__all__ = ["CorpusDatabase"]
