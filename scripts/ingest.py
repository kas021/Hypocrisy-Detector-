"""Convenient wrapper around :mod:`backend.ingest`."""
from __future__ import annotations

import sys

from backend.ingest import main as ingest_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        args = ["--srt", "samples/media/your_clip.srt", "--title", "Sample"]
    return ingest_main(args)


if __name__ == "__main__":
    sys.exit(main())
