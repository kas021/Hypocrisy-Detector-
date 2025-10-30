"""Thin wrapper for backend.scraper.run"""
from __future__ import annotations

import sys

from backend.scraper.run import main


if __name__ == "__main__":
    sys.exit(main())
