"""
Database layer for scraper module.

Provides functions to store scraped content in SQLite database.
"""

import sqlite3
import json
import os
from typing import Optional, List
from datetime import datetime
from pathlib import Path

# Import from parent if available, otherwise use local definitions
try:
    from backend.db import get_db_connection, DATA_DIR
except ImportError:
    # Fallback implementation
    DATA_DIR = os.environ.get('DATA_DIR', 'data')

    def get_db_connection(db_path: Optional[str] = None):
        """Get database connection."""
        if db_path is None:
            os.makedirs(DATA_DIR, exist_ok=True)
            db_path = os.path.join(DATA_DIR, 'contradictions.db')

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def init_db(conn: sqlite3.Connection):
    """Initialize database schema if needed."""
    cursor = conn.cursor()

    # Create sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            published_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create segments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            ts_start REAL,
            ts_end REAL,
            meta_json TEXT,
            embedding BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    """)

    # Create index on source_id for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_segments_source_id 
        ON segments(source_id)
    """)

    conn.commit()


def insert_source(
    conn: sqlite3.Connection,
    source_type: str,
    title: str,
    url: str,
    published_at: Optional[datetime] = None,
) -> int:
    """
    Insert a source into the database.

    Returns:
        source_id: ID of inserted source
    """
    cursor = conn.cursor()

    published_str = None
    if published_at:
        published_str = published_at.isoformat()

    try:
        cursor.execute("""
            INSERT INTO sources (source_type, title, url, published_at)
            VALUES (?, ?, ?, ?)
        """, (source_type, title, url, published_str))

        conn.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError:
        # URL already exists, get existing ID
        cursor.execute("SELECT id FROM sources WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            return row[0]
        raise


def insert_segments(
    conn: sqlite3.Connection,
    source_id: int,
    segments: List,
) -> List[int]:
    """
    Insert segments into the database.

    Args:
        source_id: ID of the source
        segments: List of Segment objects

    Returns:
        List of segment IDs
    """
    cursor = conn.cursor()
    segment_ids = []

    for segment in segments:
        meta_json_str = json.dumps(segment.meta_json) if segment.meta_json else None

        cursor.execute("""
            INSERT INTO segments (source_id, text, ts_start, ts_end, meta_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            source_id,
            segment.text,
            segment.ts_start,
            segment.ts_end,
            meta_json_str,
        ))

        segment_ids.append(cursor.lastrowid)

    conn.commit()
    return segment_ids


def save_raw_text(source_id: int, text: str, data_dir: Optional[str] = None):
    """Save raw text to file for debugging."""
    if data_dir is None:
        data_dir = DATA_DIR

    raw_dir = os.path.join(data_dir, 'raw')
    os.makedirs(raw_dir, exist_ok=True)

    filepath = os.path.join(raw_dir, f"{source_id}.txt")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)


def get_segments_without_embeddings(
    conn: sqlite3.Connection,
    limit: Optional[int] = None,
) -> List[dict]:
    """Get segments that need embeddings."""
    cursor = conn.cursor()

    query = """
        SELECT id, text
        FROM segments
        WHERE embedding IS NULL
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def update_segment_embedding(
    conn: sqlite3.Connection,
    segment_id: int,
    embedding: bytes,
):
    """Update segment with embedding."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE segments SET embedding = ? WHERE id = ?",
        (embedding, segment_id)
    )
    conn.commit()
