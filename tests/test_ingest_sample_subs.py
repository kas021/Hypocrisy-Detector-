from pathlib import Path

import pytest

pytest.importorskip("sqlite_utils", reason="sqlite-utils is required for ingestion tests")

from backend import ingest
from backend.db import CorpusDatabase


class DummyEmbedder:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_ingest_sample_subtitle(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", "data/test_ingest")
    monkeypatch.setattr(ingest, "SentenceTransformer", DummyEmbedder)
    ingest._EMBEDDER = None
    count = ingest.ingest_subtitle(Path("samples/media/your_clip.srt"), source_title="Sample clip")
    assert count > 0
    db = CorpusDatabase()
    segments = list(db.db.table("segments").rows)
    assert len(segments) >= count
