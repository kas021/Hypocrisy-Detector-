"""SQLite helpers for storing transcripts and embeddings."""
from __future__ import annotations

import json
from typing import Iterable, List, Optional, Tuple

import numpy as np
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
        self.db.table("sources").create(
            {
                "id": int,
                "title": str,
                "source_type": str,
                "url_or_path": str,
            },
            pk="id",
            if_not_exists=True,
        )
        self.db.table("sources").create_index(["url_or_path"], if_not_exists=True, unique=True)
        self.db.table("segments").create(
            {
                "id": int,
                "source_id": int,
                "text": str,
                "ts_start": float,
                "ts_end": float,
            },
            pk="id",
            if_not_exists=True,
        )
        self.db.table("embeddings").create(
            {
                "segment_id": int,
                "vector": str,
            },
            pk="segment_id",
            if_not_exists=True,
        )

    def add_source(self, title: str, source_type: str, url_or_path: str) -> int:
        table = self.db.table("sources")
        existing = list(table.rows_where("url_or_path = ?", [url_or_path], limit=1))
        if existing:
            source_id = existing[0]["id"]
            table.update(source_id, {"title": title, "source_type": source_type})
            return int(source_id)

        row = {"title": title, "source_type": source_type, "url_or_path": url_or_path}
        source_id = table.insert(row, pk="id")
        return int(source_id)

    def add_segment(
        self,
        source_id: int,
        text: str,
        ts_start: Optional[float],
        ts_end: Optional[float],
        embedding: Iterable[float],
    ) -> int:
        seg_table = self.db.table("segments")
        seg_id = seg_table.insert(
            {
                "source_id": source_id,
                "text": text,
                "ts_start": ts_start,
                "ts_end": ts_end,
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
                vector = np.array(json.loads(emb_row["vector"]), dtype="float32")
            except KeyError:
                vector = np.zeros(384, dtype="float32")
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
