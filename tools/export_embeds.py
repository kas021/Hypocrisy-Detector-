
import sqlite3
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DB = "backend/db.sqlite3"
MODEL_DIR = "backend/embed_model"
MODEL_NAME = "all-MiniLM-L6-v2"

def main():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, text FROM segments WHERE id NOT IN (SELECT segment_id FROM embeds)")
    rows = cur.fetchall()
    if not rows:
        print("✓ Precomputed 0 embeddings")
        con.close()
        return

    model_path = MODEL_DIR if Path(MODEL_DIR).exists() else MODEL_NAME
    model = SentenceTransformer(model_path)
    texts = [t for _, t in rows]
    vecs = model.encode(texts, normalize_embeddings=True).astype("float32")
    dim = int(vecs.shape[1])

    # Insert
    cur.executemany(
        "INSERT OR REPLACE INTO embeds(segment_id, dim, vector) VALUES(?,?,?)",
        [(int(seg_id), dim, vec.tobytes()) for (seg_id, _), vec in zip(rows, vecs)]
    )
    con.commit()
    con.close()
    print(f"✓ Precomputed {len(rows)} embeddings")

if __name__ == "__main__":
    main()
