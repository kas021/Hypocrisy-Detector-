"""Subtitle ingestion pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

try:  # pragma: no cover - imported lazily for helpful errors
    import srt
except ImportError:  # pragma: no cover - optional dependency hint
    srt = None  # type: ignore

try:  # pragma: no cover - imported lazily
    import webvtt
except ImportError:  # pragma: no cover
    webvtt = None  # type: ignore

try:  # pragma: no cover
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

from .config import REPO_ROOT, ensure_dirs
from .db import CorpusDatabase

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _load_subtitle(path: Path) -> List[Tuple[str, float | None, float | None]]:
    if path.suffix.lower() == ".srt":
        if srt is None:
            raise RuntimeError("Install the 'srt' package to parse subtitle files")
        content = path.read_text(encoding="utf-8")
        subtitles = list(srt.parse(content))
        return [
            (subtitle.content.replace("\n", " ").strip(), subtitle.start.total_seconds(), subtitle.end.total_seconds())
            for subtitle in subtitles
            if subtitle.content.strip()
        ]
    if path.suffix.lower() == ".vtt":
        if webvtt is None:
            raise RuntimeError("Install the 'webvtt-py' package to parse VTT files")
        captions = webvtt.read(str(path))
        results = []
        for caption in captions:
            text = caption.text.replace("\n", " ").strip()
            if not text:
                continue
            start = caption.start_in_seconds
            end = caption.end_in_seconds
            results.append((text, start, end))
        return results
    raise ValueError("Unsupported subtitle format. Use .srt or .vtt")


def _normalize_statements(statements: Iterable[Tuple[str, float | None, float | None]]):
    normalized = []
    for text, start, end in statements:
        cleaned = " ".join(text.split())
        if cleaned:
            normalized.append((cleaned, start, end))
    return normalized


def ingest_subtitle(subtitle_path: Path, source_title: str | None = None) -> int:
    ensure_dirs()
    subtitle_path = _repo_path(subtitle_path)
    if not subtitle_path.exists():
        print(f"Subtitle file not found: {subtitle_path}", file=sys.stderr)
        return 0

    statements = _normalize_statements(_load_subtitle(subtitle_path))
    if not statements:
        print("No statements found in subtitle file", file=sys.stderr)
        return 0

    if SentenceTransformer is None:
        raise RuntimeError("Install sentence-transformers to generate embeddings")

    model = SentenceTransformer(_MODEL_NAME)
    embeddings = model.encode([text for text, _, _ in statements])

    db = CorpusDatabase()
    source_title = source_title or subtitle_path.stem
    try:
        relative_path = subtitle_path.relative_to(REPO_ROOT)
    except ValueError:
        relative_path = subtitle_path

    source_id = db.add_source(
        title=source_title,
        source_type="subtitle",
        url_or_path=str(relative_path),
    )

    for (text, start, end), vector in zip(statements, embeddings):
        db.add_segment(
            source_id=source_id,
            text=text,
            ts_start=start,
            ts_end=end,
            embedding=vector,
        )

    print(f"Ingested {len(statements)} segments from {subtitle_path}")
    return len(statements)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest subtitle files into the corpus")
    parser.add_argument("--subtitle", required=True, help="Path to .srt or .vtt subtitle file")
    parser.add_argument("--title", help="Optional human readable title")
    args = parser.parse_args(argv)

    try:
        count = ingest_subtitle(Path(args.subtitle), source_title=args.title)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if count == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
