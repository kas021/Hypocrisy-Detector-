
## Scraping Sources

The project includes a pluggable scraper module that can collect content from various sources while respecting robots.txt and site terms of service.

### Supported Providers

- **YouTube**: Video transcripts using `youtube-transcript-api` and metadata via `yt-dlp`
- **RSS/Atom Feeds**: Official newsrooms and blogs via `feedparser`
- **Wikipedia**: Articles via the official REST API
- **GOV.UK**: UK government publications via RSS feeds
- **UK Parliament Hansard**: Parliamentary debates and speeches
- **Generic Web Pages**: Any whitelisted domain using `trafilatura`

### Installation

Install scraper dependencies:

```bash
pip install requests feedparser trafilatura youtube-transcript-api yt-dlp sentence-transformers
```

### Usage

The scraper can be run from the command line. All commands support dry-run mode (default) and commit mode with `--commit`.

#### YouTube Videos

```bash
# Dry run (preview only)
python -m backend.scraper.run youtube --url https://www.youtube.com/watch?v=VIDEO_ID

# Commit to database with embeddings
python -m backend.scraper.run youtube --url https://www.youtube.com/watch?v=VIDEO_ID --commit --embed
```

#### RSS Feeds

```bash
# GOV.UK announcements
python -m backend.scraper.run rss --url https://www.gov.uk/government/announcements.atom --commit --embed

# Limit to first 10 items
python -m backend.scraper.run rss --url https://example.com/feed.xml --limit 10 --commit
```

#### Wikipedia

```bash
# By page title
python -m backend.scraper.run wikipedia --page "Artificial intelligence" --commit --embed

# By URL
python -m backend.scraper.run wikipedia --url https://en.wikipedia.org/wiki/Climate_change --commit
```

#### UK Parliament Hansard

```bash
# Search debates by keyword and date range
python -m backend.scraper.run hansard --q "immigration" --from 2025-01-01 --to 2025-10-30 --commit
```

#### Generic Web Pages

```bash
# Whitelist domains and scrape
python -m backend.scraper.run generic --allow bbc.co.uk,apnews.com --url https://www.bbc.co.uk/news/article1 https://apnews.com/article2 --commit --embed
```

### Configuration

Set environment variables for scraper behavior:

```bash
# Contact email for User-Agent string (required for polite scraping)
export SCRAPER_CONTACT="your-email@example.com"

# Data directory (default: 'data')
export DATA_DIR="./data"
```

### Safety Features

1. **robots.txt Compliance**: Automatically checks and respects robots.txt directives. Fails closed if robots.txt disallows access.

2. **Rate Limiting**: Default maximum of 1 request per second with random polite delays.

3. **Domain Whitelisting**: Generic provider only scrapes from explicitly allowed domains.

4. **User Agent**: Identifies the scraper with contact information.

### Database Integration

Scraped content is stored in SQLite with the following schema:

**sources** table:
- `id`: Primary key
- `source_type`: Provider type (youtube, rss, wikipedia, etc.)
- `title`: Content title
- `url`: Source URL
- `published_at`: Publication date
- `created_at`: When scraped

**segments** table:
- `id`: Primary key
- `source_id`: Foreign key to sources
- `text`: Segment text content
- `ts_start`: Start timestamp (for videos)
- `ts_end`: End timestamp (for videos)
- `meta_json`: Additional metadata as JSON
- `embedding`: Vector embedding (BLOB)
- `created_at`: When created

Raw text is also saved to `DATA_DIR/raw/<source_id>.txt` for debugging.

### Embeddings

The scraper can automatically generate embeddings using sentence-transformers:

```bash
# Generate embeddings during scraping
python -m backend.scraper.run youtube --url VIDEO_URL --commit --embed

# Generate embeddings for existing segments
python -c "from backend.scraper.db import get_db_connection; from backend.scraper.embeddings import embed_segments; conn = get_db_connection(); embed_segments(conn); conn.close()"
```

Default model: `all-MiniLM-L6-v2` (384-dimensional embeddings)

### Testing

Run scraper tests:

```bash
python -m pytest tests/test_scraper.py -v
```

Or with unittest:

```bash
python -m unittest tests.test_scraper
```

### Example Workflow

Complete workflow to scrape, store, and analyze content:

```bash
# 1. Scrape sources
python -m backend.scraper.run youtube --url https://www.youtube.com/watch?v=VIDEO_ID --commit --embed
python -m backend.scraper.run rss --url https://www.gov.uk/government/announcements.atom --limit 5 --commit --embed

# 2. Add subtitle files (if using existing ingest pipeline)
python backend/ingest.py --subtitle samples/media/your_clip.srt

# 3. Start the web app
uvicorn frontend.app:app --host 127.0.0.1 --port 7860
```

### Limitations

- **YouTube**: Requires videos to have transcripts/captions available
- **Hansard**: API structure may vary; implementation may need adjustments based on actual API
- **Rate Limits**: Respects 1 RPS by default; some sites may have stricter limits
- **Authentication**: Does not support authenticated access; only public content

### Extending with New Providers

To add a new provider:

1. Create a class inheriting from `Provider` in `backend/scraper/providers.py`
2. Implement the `collect()` method returning `Iterable[Tuple[Source, List[Segment]]]`
3. Add CLI command in `backend/scraper/run.py`
4. Add tests in `tests/test_scraper.py`

Example:

```python
class MyProvider(Provider):
    def collect(self, url: str, **kwargs):
        # Check robots.txt
        if not self.check_robots_txt(url):
            return

        # Rate limit
        self.rate_limiter.wait()

        # Fetch content
        response = self.session.get(url)

        # Parse and yield
        source = Source(
            source_type='myprovider',
            title='Title',
            url=url,
        )

        segments = [Segment(text='...')]

        yield source, segments
```
