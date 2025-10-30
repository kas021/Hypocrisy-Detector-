
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingRetriever:
    def __init__(self, db_path: str, embed_model_dir: str = "backend/embed_model", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.embed_model_dir = embed_model_dir
        # Load local model if downloaded; else fallback to remote
        model_path = embed_model_dir if Path(embed_model_dir).exists() else model_name
        self.model = SentenceTransformer(model_path)

    # --- DB helpers ---
    def _connect(self):
        return sqlite3.connect(self.db_path)

    def encode(self, text: str) -> np.ndarray:
        v = self.model.encode([text], normalize_embeddings=True)[0]
        return v.astype("float32")

    def get_segments_with_embeddings(self) -> List[Tuple[int, np.ndarray]]:
        con = self._connect()
        cur = con.cursor()
        cur.execute("SELECT segment_id, dim, vector FROM embeds")
        rows = cur.fetchall()
        con.close()
        out = []
        for seg_id, dim, blob in rows:
            vec = np.frombuffer(blob, dtype="float32")
            if vec.size != dim:
                continue
            out.append((seg_id, vec))
        return out

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        q = self.encode(query)
        items = self.get_segments_with_embeddings()
        if not items:
            return []
        ids, mat = zip(*items)
        M = np.stack(mat, axis=0)  # N x D
        # Cosine similarities since vectors are normalized
        sims = (M @ q).tolist()
        ranked = sorted(zip(ids, sims), key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch segment + doc metadata
        con = self._connect()
        cur = con.cursor()
        results = []
        for seg_id, score in ranked:
            cur.execute("""
                SELECT s.id, s.start_ms, s.end_ms, s.text, d.id, d.source, d.url, d.date, d.title, d.media_path
                FROM segments s JOIN documents d ON s.document_id = d.id
                WHERE s.id = ?
            """, (seg_id,))
            row = cur.fetchone()
            if row:
                results.append({
                    "segment_id": row[0],
                    "start_ms": row[1],
                    "end_ms": row[2],
                    "text": row[3],
                    "document_id": row[4],
                    "source": row[5],
                    "url": row[6],
                    "date": row[7],
                    "title": row[8],
                    "media_path": row[9],
                    "embed_score": float(score),
                })
        con.close()
        return results
