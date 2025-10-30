
# File 5: backend/scraper/run.py - CLI entrypoint
run_content = '''#!/usr/bin/env python3
"""
CLI entrypoint for scraper module.

Usage:
    python -m backend.scraper.run youtube --url <url>
    python -m backend.scraper.run rss --url <url>
    python -m backend.scraper.run wikipedia --page <title>
    python -m backend.scraper.run hansard --q <query> --from <date> --to <date>
    python -m backend.scraper.run generic --allow <domains> --url <urls>
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from .providers import (
    YouTubeProvider,
    RSSProvider,
    WikipediaProvider,
    GovUkProvider,
    HansardProvider,
    GenericProvider,
)
from .db import (
    get_db_connection,
    init_db,
    insert_source,
    save_raw_text,
)
from .embeddings import index_segments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scrape_youtube(args):
    """Scrape YouTube video."""
    provider = YouTubeProvider()
    
    for source, segments in provider.collect(url=args.url, video_id=args.video_id):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run - print JSON preview
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                    'published_at': source.published_at.isoformat() if source.published_at else None,
                },
                'segments_count': len(segments),
                'sample_segments': [
                    {
                        'text': seg.text[:100] + '...' if len(seg.text) > 100 else seg.text,
                        'ts_start': seg.ts_start,
                        'ts_end': seg.ts_end,
                    }
                    for seg in segments[:3]
                ],
            }
            print(json.dumps(preview, indent=2))


def scrape_rss(args):
    """Scrape RSS feed."""
    provider = RSSProvider()
    
    count = 0
    for source, segments in provider.collect(url=args.url):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                },
                'segments_count': len(segments),
            }
            print(json.dumps(preview, indent=2))
        
        count += 1
        if args.limit and count >= args.limit:
            break


def scrape_wikipedia(args):
    """Scrape Wikipedia page."""
    provider = WikipediaProvider()
    
    for source, segments in provider.collect(page=args.page, url=args.url):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                },
                'segments_count': len(segments),
                'sample_segments': [
                    seg.text[:100] + '...' if len(seg.text) > 100 else seg.text
                    for seg in segments[:3]
                ],
            }
            print(json.dumps(preview, indent=2))


def scrape_govuk(args):
    """Scrape GOV.UK RSS feed."""
    provider = GovUkProvider()
    
    count = 0
    for source, segments in provider.collect(url=args.url):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                },
                'segments_count': len(segments),
            }
            print(json.dumps(preview, indent=2))
        
        count += 1
        if args.limit and count >= args.limit:
            break


def scrape_hansard(args):
    """Scrape Hansard debates."""
    provider = HansardProvider()
    
    for source, segments in provider.collect(
        query=args.q,
        from_date=args.from_date,
        to_date=args.to_date,
    ):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                },
                'segments_count': len(segments),
            }
            print(json.dumps(preview, indent=2))
'''

run_content_part2 = '''

def scrape_generic(args):
    """Scrape generic web pages."""
    # Parse allowed domains
    allowed_domains = [d.strip() for d in args.allow.split(',')]
    
    # Parse URLs
    urls = []
    if args.url:
        if isinstance(args.url, list):
            urls = args.url
        else:
            urls = [args.url]
    
    provider = GenericProvider(allowed_domains=allowed_domains)
    
    for source, segments in provider.collect(urls=urls):
        if args.commit:
            conn = get_db_connection(args.data_dir)
            init_db(conn)
            
            source_id = insert_source(
                conn,
                source.source_type,
                source.title,
                source.url,
                source.published_at,
            )
            
            # Save raw text
            raw_text = '\\n\\n'.join(seg.text for seg in segments)
            save_raw_text(source_id, raw_text)
            
            # Index segments
            index_segments(conn, source_id, segments, args.embed)
            
            logger.info(f"Saved source {source_id} with {len(segments)} segments")
            conn.close()
        else:
            # Dry run
            preview = {
                'source': {
                    'type': source.source_type,
                    'title': source.title,
                    'url': source.url,
                },
                'segments_count': len(segments),
            }
            print(json.dumps(preview, indent=2))


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description='Scrape content for contradiction detection'
    )
    
    # Global options
    parser.add_argument(
        '--data-dir',
        type=str,
        help='Data directory (default: from config or DATA_DIR env var)'
    )
    parser.add_argument(
        '--commit',
        action='store_true',
        help='Write to database (default: dry-run)'
    )
    parser.add_argument(
        '--embed',
        action='store_true',
        help='Generate embeddings after insertion'
    )
    
    subparsers = parser.add_subparsers(dest='provider', help='Provider type')
    
    # YouTube provider
    youtube_parser = subparsers.add_parser('youtube', help='Scrape YouTube videos')
    youtube_parser.add_argument('--url', type=str, help='YouTube video URL')
    youtube_parser.add_argument('--video-id', type=str, help='YouTube video ID')
    youtube_parser.set_defaults(func=scrape_youtube)
    
    # RSS provider
    rss_parser = subparsers.add_parser('rss', help='Scrape RSS feeds')
    rss_parser.add_argument('--url', type=str, required=True, help='RSS feed URL')
    rss_parser.add_argument('--limit', type=int, help='Max items to process')
    rss_parser.set_defaults(func=scrape_rss)
    
    # Wikipedia provider
    wiki_parser = subparsers.add_parser('wikipedia', help='Scrape Wikipedia')
    wiki_parser.add_argument('--page', type=str, help='Page title')
    wiki_parser.add_argument('--url', type=str, help='Wikipedia URL')
    wiki_parser.set_defaults(func=scrape_wikipedia)
    
    # GOV.UK provider
    govuk_parser = subparsers.add_parser('govuk', help='Scrape GOV.UK RSS')
    govuk_parser.add_argument('--url', type=str, required=True, help='GOV.UK RSS URL')
    govuk_parser.add_argument('--limit', type=int, help='Max items to process')
    govuk_parser.set_defaults(func=scrape_govuk)
    
    # Hansard provider
    hansard_parser = subparsers.add_parser('hansard', help='Scrape Hansard')
    hansard_parser.add_argument('--q', type=str, required=True, help='Search query')
    hansard_parser.add_argument('--from', dest='from_date', type=str, help='Start date (YYYY-MM-DD)')
    hansard_parser.add_argument('--to', dest='to_date', type=str, help='End date (YYYY-MM-DD)')
    hansard_parser.set_defaults(func=scrape_hansard)
    
    # Generic provider
    generic_parser = subparsers.add_parser('generic', help='Scrape generic sites')
    generic_parser.add_argument(
        '--allow',
        type=str,
        required=True,
        help='Comma-separated allowed domains'
    )
    generic_parser.add_argument(
        '--url',
        type=str,
        nargs='+',
        required=True,
        help='URLs to scrape'
    )
    generic_parser.set_defaults(func=scrape_generic)
    
    args = parser.parse_args()
    
    if not args.provider:
        parser.print_help()
        sys.exit(1)
    
    # Execute provider function
    args.func(args)


if __name__ == '__main__':
    main()
'''

print("Generated run.py parts 1 and 2")
print(f"Run content part 1 length: {len(run_content)}")
print(f"Run content part 2 length: {len(run_content_part2)}")
