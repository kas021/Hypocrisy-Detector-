
# Create quick reference card
quick_reference = '''# Scraper Module - Quick Reference Card

## Installation

```bash
pip install requests feedparser trafilatura youtube-transcript-api yt-dlp sentence-transformers
export SCRAPER_CONTACT="your-email@example.com"
```

## Basic Commands

### Dry Run (Preview Only)
```bash
python -m backend.scraper.run <provider> [options]
```

### Commit to Database
```bash
python -m backend.scraper.run <provider> [options] --commit
```

### With Embeddings
```bash
python -m backend.scraper.run <provider> [options] --commit --embed
```

## Providers

| Provider | Command | Required Args | Example |
|----------|---------|---------------|---------|
| YouTube | `youtube` | `--url` or `--video-id` | `--url https://youtube.com/watch?v=...` |
| RSS | `rss` | `--url` | `--url https://example.com/feed.xml` |
| Wikipedia | `wikipedia` | `--page` or `--url` | `--page "Topic"` |
| GOV.UK | `govuk` | `--url` | `--url https://gov.uk/feed.atom` |
| Hansard | `hansard` | `--q` | `--q "keyword" --from 2025-01-01` |
| Generic | `generic` | `--allow`, `--url` | `--allow bbc.co.uk --url URL` |

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--commit` | Write to database | Dry-run |
| `--embed` | Generate embeddings | No embeddings |
| `--data-dir` | Data directory | `$DATA_DIR` or `data/` |
| `--limit` | Max items (RSS only) | All items |

## Examples

### YouTube Video
```bash
python -m backend.scraper.run youtube \\
  --url https://www.youtube.com/watch?v=dQw4w9WgXcQ \\
  --commit --embed
```

### RSS Feed
```bash
python -m backend.scraper.run rss \\
  --url https://www.gov.uk/government/announcements.atom \\
  --limit 10 --commit
```

### Wikipedia
```bash
python -m backend.scraper.run wikipedia \\
  --page "Artificial intelligence" \\
  --commit --embed
```

### Multiple Web Pages
```bash
python -m backend.scraper.run generic \\
  --allow bbc.co.uk,apnews.com \\
  --url https://bbc.co.uk/news/article1 https://apnews.com/article2 \\
  --commit
```

## Database Schema

### sources table
- `id`, `source_type`, `title`, `url`, `published_at`, `created_at`

### segments table
- `id`, `source_id`, `text`, `ts_start`, `ts_end`, `meta_json`, `embedding`, `created_at`

## Query Database

```bash
# View sources
sqlite3 data/contradictions.db "SELECT * FROM sources LIMIT 5;"

# Count segments
sqlite3 data/contradictions.db "SELECT COUNT(*) FROM segments;"

# Check embeddings
sqlite3 data/contradictions.db "SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL;"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Run from project root: `cd /path/to/project` |
| Robots.txt blocks | Choose different source (by design) |
| No transcript | Video lacks captions |
| Missing embeddings | Run with `--embed` flag |

## Safety Features

✅ Respects robots.txt (fail closed)
✅ Rate limiting (1 RPS default)
✅ Domain whitelisting (generic provider)
✅ Identifies scraper in User-Agent
✅ No authentication/login support

## Files

| File | Purpose |
|------|---------|
| `backend/scraper/__init__.py` | Module exports |
| `backend/scraper/providers.py` | Provider implementations |
| `backend/scraper/db.py` | Database operations |
| `backend/scraper/embeddings.py` | Embedding generation |
| `backend/scraper/run.py` | CLI interface |
| `tests/test_scraper.py` | Unit tests |

## Testing

```bash
# Run tests
pytest tests/test_scraper.py -v

# Test dry run
python -m backend.scraper.run youtube --url YOUTUBE_URL

# Test database write
python -m backend.scraper.run wikipedia --page "Test" --commit
```

## Custom Provider Template

```python
class MyProvider(Provider):
    def collect(self, url: str, **kwargs):
        if not self.check_robots_txt(url):
            return
        self.rate_limiter.wait()
        
        # Fetch and parse
        source = Source('mytype', 'Title', url)
        segments = [Segment('Text here')]
        
        yield source, segments
```
'''

# Write quick reference
with open('QUICK_REFERENCE.md', 'w', encoding='utf-8') as f:
    f.write(quick_reference)

print("Created QUICK_REFERENCE.md")
print(f"Quick reference length: {len(quick_reference)} characters")
