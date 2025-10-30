"""Content ingestion pipeline for the hypocrisy corpus."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

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
_EMBEDDER = None


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


def _ensure_embedder():
    global _EMBEDDER
    if SentenceTransformer is None:
        raise RuntimeError("Install sentence-transformers to generate embeddings")
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer(_MODEL_NAME)
    return _EMBEDDER


def _ingest_segments(
    *,
    statements: Sequence[Tuple[str, float | None, float | None]],
    source_title: str,
    source_type: str,
    url_or_path: str,
    doc_id_prefix: str | None = None,
    published_at: dt.datetime | None = None,
    author: str | None = None,
    extra: dict | None = None,
) -> int:
    if not statements:
        return 0
    embedder = _ensure_embedder()
    embeddings = embedder.encode([text for text, _, _ in statements])

    db = CorpusDatabase()
    try:
        relative_path = Path(url_or_path).relative_to(REPO_ROOT)
        url_value = str(relative_path)
    except ValueError:
        url_value = url_or_path

    source_id = db.add_source(
        title=source_title,
        source_type=source_type,
        url_or_path=url_value,
        published_at=published_at,
        author=author,
        extra=extra,
    )

    for index, ((text, start, end), vector) in enumerate(zip(statements, embeddings), start=1):
        doc_id = f"{doc_id_prefix}:{index}" if doc_id_prefix else None
        db.add_segment(
            source_id=source_id,
            text=text,
            ts_start=start,
            ts_end=end,
            embedding=vector,
            doc_id=doc_id,
        )
    return len(statements)


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

    source_title = source_title or subtitle_path.stem
    count = _ingest_segments(
        statements=statements,
        source_title=source_title,
        source_type="subtitle",
        url_or_path=str(subtitle_path),
        doc_id_prefix=subtitle_path.stem,
    )
    if count:
        print(f"Ingested {count} segments from {subtitle_path}")
    return count


def ingest_text_file(text_path: Path, source_title: str | None = None) -> int:
    ensure_dirs()
    text_path = _repo_path(text_path)
    if not text_path.exists():
        print(f"Text file not found: {text_path}", file=sys.stderr)
        return 0
    content = text_path.read_text(encoding="utf-8")
    statements = [
        (chunk.strip(), None, None)
        for chunk in content.splitlines()
        if chunk.strip()
    ]
    if not statements:
        print("Text file did not contain any statements", file=sys.stderr)
        return 0
    source_title = source_title or text_path.stem
    count = _ingest_segments(
        statements=statements,
        source_title=source_title,
        source_type="text",
        url_or_path=str(text_path),
        doc_id_prefix=text_path.stem,
    )
    if count:
        print(f"Ingested {count} statements from {text_path}")
    return count


def ingest_text_snippet(text: str, source_title: str) -> int:
    statements = [
        (chunk.strip(), None, None)
        for chunk in text.splitlines()
        if chunk.strip()
    ]
    if not statements:
        return 0
    return _ingest_segments(
        statements=statements,
        source_title=source_title,
        source_type="text",
        url_or_path=source_title,
        doc_id_prefix=source_title,
    )


def ingest_scraped_items(items: Iterable[dict | object]) -> int:
    ensure_dirs()
    total = 0
    for raw in items:
        if hasattr(raw, "dict"):
            data = raw.dict()  # type: ignore[attr-defined]
        elif isinstance(raw, dict):
            data = raw
        else:
            data = {k: getattr(raw, k) for k in dir(raw) if not k.startswith("_")}
        text = data.get("text")
        if not text:
            continue
        url = data.get("url") or data.get("source_url") or ""
        title = data.get("title") or "Untitled"
        source_name = data.get("source_name") or data.get("provider") or "scraper"
        published = data.get("published_at")
        if isinstance(published, str):
            try:
                published_at = dt.datetime.fromisoformat(published)
            except ValueError:
                published_at = None
        else:
            published_at = published
        statements = [(text.strip(), None, None)]
        extra = {
            k: v
            for k, v in data.items()
            if k
            not in {"text", "title", "url", "source_url", "source_name", "published_at"}
        }
        count = _ingest_segments(
            statements=statements,
            source_title=title,
            source_type=f"scraped:{source_name}",
            url_or_path=url or title,
            doc_id_prefix=data.get("id"),
            published_at=published_at,
            author=data.get("author"),
            extra=extra,
        )
        total += count
    if total:
        print(f"Ingested {total} scraped statements")
    return total


def ingest_from_scraped_sqlite(path: Path) -> int:
    path = _repo_path(path)
    if not path.exists():
        print(f"Scraped SQLite database not found: {path}", file=sys.stderr)
        return 0
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM raw_items").fetchall()
    except sqlite3.Error as exc:
        print(f"Unable to read scraped database: {exc}", file=sys.stderr)
        conn.close()
        return 0
    items = []
    for row in rows:
        getter = row.__getitem__ if hasattr(row, "__getitem__") else lambda key: row[key]
        media_blob = getter("media_urls_json") if "media_urls_json" in row.keys() else None
        extra_blob = getter("extra_json") if "extra_json" in row.keys() else None
        items.append(
            {
                "id": getter("id") if "id" in row.keys() else getter("url"),
                "url": getter("url"),
                "title": getter("title"),
                "text": getter("text"),
                "source_name": getter("source_name"),
                "published_at": getter("published_at"),
                "author": getter("author"),
                "media_urls": json.loads(media_blob) if media_blob else [],
                "raw_html": getter("raw_html"),
                "license": getter("license"),
                "extra": json.loads(extra_blob) if extra_blob else {},
            }
        )
    conn.close()
    return ingest_scraped_items(items)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest content into the hypocrisy corpus")
    parser.add_argument("--srt", help="Path to .srt subtitle file")
    parser.add_argument("--text", help="Path to plain text file")
    parser.add_argument("--from-scraped", help="Path to scraped sqlite database")
    parser.add_argument("--title", help="Optional human readable title")
    args = parser.parse_args(argv)

    try:
        if args.srt:
            count = ingest_subtitle(Path(args.srt), source_title=args.title)
        elif args.text:
            count = ingest_text_file(Path(args.text), source_title=args.title)
        elif args.from_scraped:
            count = ingest_from_scraped_sqlite(Path(args.from_scraped))
        else:
            parser.error("Provide --srt, --text, or --from-scraped")
            return 1
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if count == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
