"""Command-line entry point for running scraper providers."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .base import Provider
from .storage import RawItemStore
from .providers import PROVIDERS

LOGGER = logging.getLogger(__name__)


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--since must be ISO format YYYY-MM-DD")


def _select_providers(slugs: Iterable[str]) -> List[Provider]:
    selected: List[Provider] = []
    for slug in slugs:
        cls = PROVIDERS.get(slug)
        if not cls:
            raise argparse.ArgumentTypeError(f"Unknown provider '{slug}'")
        selected.append(cls())
    return selected


def run_scraper(
    *,
    providers: List[Provider],
    since: datetime | None,
    limit: int | None,
    out_path: Path,
) -> dict:
    summary: dict[str, dict[str, int]] = {}
    with RawItemStore(out_path) as store:
        for provider in providers:
            LOGGER.info("Fetching from provider %s", provider.slug)
            items = list(provider.fetch(since=since, limit=limit))
            inserted, updated = store.upsert_items(items)
            summary[provider.slug] = {
                "fetched": len(items),
                "inserted": inserted,
                "updated": updated,
            }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch new hypocrisy corpus sources")
    parser.add_argument(
        "--providers",
        default=",".join(PROVIDERS.keys()),
        help="Comma-separated list of providers to run",
    )
    parser.add_argument("--since", help="ISO date (YYYY-MM-DD) to limit results")
    parser.add_argument("--limit", type=int, help="Max items per provider")
    parser.add_argument(
        "--out",
        default="data/raw/scraped.sqlite",
        help="Path to SQLite database for raw items",
    )
    args = parser.parse_args(argv)

    since = _parse_since(args.since) if args.since else None
    provider_slugs = [slug.strip() for slug in args.providers.split(",") if slug.strip()]
    providers = _select_providers(provider_slugs)
    out_path = Path(args.out)

    summary = run_scraper(providers=providers, since=since, limit=args.limit, out_path=out_path)
    for slug, counts in summary.items():
        print(f"{slug}: fetched={counts['fetched']} inserted={counts['inserted']} updated={counts['updated']}")
    print(f"Raw items stored in {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
