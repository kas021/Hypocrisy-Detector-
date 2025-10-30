
import argparse
import datetime as dt
import json
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Iterable, Tuple

import srt
import webvtt

# --- Database ---

def init_db(db_path: str) -> None:
    """
    Create a fresh SQLite database with the schema we need.
    Safe to run multiple times.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            url TEXT,
            date TEXT,
            title TEXT,
            media_path TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeds (
            segment_id INTEGER PRIMARY KEY,
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL,
            FOREIGN KEY(segment_id) REFERENCES segments(id)
        );
    """)
    con.commit()
    con.close()

# --- Subtitle parsing ---

def _to_ms(td) -> int:
    return int(td.total_seconds() * 1000)

def parse_srt(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    items = list(srt.parse(data))
    out = []
    for it in items:
        out.append({
            "start_ms": _to_ms(it.start - dt.timedelta(0)),
            "end_ms": _to_ms(it.end - dt.timedelta(0)),
            "text": it.content.replace("\n", " ").strip(),
        })
    return out

def parse_vtt(path: str) -> List[Dict]:
    out = []
    for caption in webvtt.read(path):
        start = _parse_ts_to_ms(caption.start)
        end = _parse_ts_to_ms(caption.end)
        text = caption.text.replace("\n", " ").strip()
        out.append({"start_ms": start, "end_ms": end, "text": text})
    return out

def _parse_ts_to_ms(ts: str) -> int:
    # VTT timestamps: HH:MM:SS.mmm
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(".")
    total = (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms.ljust(3, "0")[:3])
    return total

def parse_jsonl(path: str) -> List[Dict]:
    # Each line: {"start_ms": int, "end_ms": int, "text": str}
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            out.append({"start_ms": int(obj["start_ms"]), "end_ms": int(obj["end_ms"]), "text": str(obj["text"]).strip()})
    return out

def parse_subtitles(path: str) -> List[Dict]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".srt":
        return parse_srt(str(p))
    if ext == ".vtt":
        return parse_vtt(str(p))
    if ext == ".jsonl":
        return parse_jsonl(str(p))
    raise ValueError(f"Unsupported subtitle format: {ext}")

# --- Ingest ---

def ingest_document(
    db_path: str,
    video_path: str,
    transcript_path: str,
    source: str,
    date: str,
    title: str,
    url: str,
) -> int:
    """
    Insert a document and its subtitle segments into the DB.
    Returns the document_id.
    """
    if not Path(transcript_path).exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")
    segs = parse_subtitles(transcript_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO documents(source,url,date,title,media_path) VALUES(?,?,?,?,?)",
        (source, url, date, title, video_path),
    )
    doc_id = cur.lastrowid
    cur.executemany(
        "INSERT INTO segments(document_id,start_ms,end_ms,text) VALUES(?,?,?,?)",
        [(doc_id, s["start_ms"], s["end_ms"], s["text"]) for s in segs],
    )
    con.commit()
    con.close()
    return doc_id

# --- CLI ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to SQLite database file")
    ap.add_argument("--video", required=False, default="", help="Optional: path to video file for reference")
    ap.add_argument("--subtitle", required=True, help="Path to transcript (.srt|.vtt|.jsonl)")
    ap.add_argument("--source", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--title", required=True)
    ap.add_argument("--url", required=True)
    args = ap.parse_args()

    init_db(args.db)
    doc_id = ingest_document(
        db_path=args.db,
        video_path=args.video,
        transcript_path=args.subtitle,
        source=args.source,
        date=args.date,
        title=args.title,
        url=args.url,
    )
    print(f"Ingested document_id={doc_id} with transcript {args.subtitle}")

if __name__ == "__main__":
    main()
