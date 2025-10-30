"""Command-line wrapper for ingesting subtitle files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.ingest import ingest_subtitle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest subtitle transcripts into the database")
    parser.add_argument(
        "--subtitle",
        default="samples/media/your_clip.srt",
        help="Relative path to an SRT or VTT file (defaults to bundled sample)",
    )
    parser.add_argument("--title", help="Optional title for the source")
    args = parser.parse_args(argv)

    count = ingest_subtitle(Path(args.subtitle), source_title=args.title)
    if count == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
