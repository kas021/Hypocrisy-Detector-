
# Create implementation guide
implementation_guide = '''# Scraper Module Implementation Guide

## Overview

This guide walks you through integrating the scraper module into the contradiction-finder repository.

## File Structure

After integration, your project structure will look like:

```
contradiction-finder/
├── backend/
│   ├── scraper/
│   │   ├── __init__.py      (new)
│   │   ├── providers.py     (new)
│   │   ├── db.py            (new)
│   │   ├── embeddings.py    (new)
│   │   └── run.py           (new)
│   ├── db.py                (existing, will be used as fallback)
│   ├── ingest.py            (existing)
│   └── config.py            (existing, optional)
├── tests/
│   └── test_scraper.py      (new)
├── requirements.txt         (update)
└── README.md                (update)
```

## Step-by-Step Installation

### 1. Create Directory Structure

```bash
mkdir -p backend/scraper
touch backend/scraper/__init__.py
```

### 2. Copy Files

Copy the generated files to their respective locations:

```bash
# Main module files
cp scraper_init.py backend/scraper/__init__.py
cp scraper_providers.py backend/scraper/providers.py
cp scraper_db.py backend/scraper/db.py
cp scraper_embeddings.py backend/scraper/embeddings.py
cp scraper_run.py backend/scraper/run.py

# Test file
cp test_scraper.py tests/test_scraper.py

# Documentation
cat scraper_readme_section.md >> README.md
```

### 3. Update Requirements

Add the scraper dependencies to your requirements.txt:

```bash
cat scraper_requirements.txt >> requirements.txt
```

Or manually add:
```
requests>=2.31.0
feedparser>=6.0.10
trafilatura>=1.6.0
youtube-transcript-api>=0.6.1
yt-dlp>=2023.11.0
sentence-transformers>=2.2.0
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Environment Variables

```bash
export SCRAPER_CONTACT="your-email@example.com"
export DATA_DIR="./data"
```

Or add to your `.env` file:
```
SCRAPER_CONTACT=your-email@example.com
DATA_DIR=./data
```

## Testing the Installation

### 1. Run Unit Tests

```bash
# Using pytest
pytest tests/test_scraper.py -v

# Or using unittest
python -m unittest tests.test_scraper
```

### 2. Test Dry Run (No Database Write)

```bash
# Test YouTube provider
python -m backend.scraper.run youtube --url https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Test Wikipedia provider
python -m backend.scraper.run wikipedia --page "Python (programming language)"
```

Expected output: JSON preview of scraped content

### 3. Test Database Write

```bash
# Scrape and commit to database
python -m backend.scraper.run youtube --url https://www.youtube.com/watch?v=dQw4w9WgXcQ --commit

# Check database
sqlite3 data/contradictions.db "SELECT * FROM sources;"
sqlite3 data/contradictions.db "SELECT COUNT(*) FROM segments;"
```

### 4. Test with Embeddings

```bash
# Scrape with automatic embedding generation
python -m backend.scraper.run wikipedia --page "Artificial intelligence" --commit --embed

# Verify embeddings
sqlite3 data/contradictions.db "SELECT COUNT(*) FROM segments WHERE embedding IS NOT NULL;"
```

## Usage Examples

### YouTube Transcripts

```bash
# Single video
python -m backend.scraper.run youtube \\
  --url https://www.youtube.com/watch?v=VIDEO_ID \\
  --commit --embed
```

### RSS Feeds

```bash
# GOV.UK announcements
python -m backend.scraper.run rss \\
  --url https://www.gov.uk/government/announcements.atom \\
  --limit 10 \\
  --commit --embed

# BBC News RSS
python -m backend.scraper.run rss \\
  --url http://feeds.bbci.co.uk/news/rss.xml \\
  --commit
```

### Wikipedia Articles

```bash
# By page title
python -m backend.scraper.run wikipedia \\
  --page "Climate change" \\
  --commit --embed

# By URL
python -m backend.scraper.run wikipedia \\
  --url https://en.wikipedia.org/wiki/Machine_learning \\
  --commit --embed
```

### UK Parliament Hansard

```bash
# Search debates
python -m backend.scraper.run hansard \\
  --q "climate change" \\
  --from 2025-01-01 \\
  --to 2025-10-30 \\
  --commit --embed
```

### Generic Web Pages

```bash
# Multiple URLs from whitelisted domains
python -m backend.scraper.run generic \\
  --allow bbc.co.uk,theguardian.com \\
  --url https://www.bbc.co.uk/news/article1 https://www.theguardian.com/article2 \\
  --commit --embed
```

## Integration with Existing Code

### Option 1: Use Existing backend/db.py

If your project already has `backend/db.py` with a `get_db_connection()` function, the scraper will automatically use it. No changes needed.

### Option 2: Standalone Usage

The scraper includes a fallback database implementation, so it can work independently if `backend/db.py` doesn't exist.

### Option 3: Custom Integration

To integrate with existing ingest pipeline:

```python
# In your existing code
from backend.scraper.providers import YouTubeProvider
from backend.scraper.db import insert_source, init_db, get_db_connection
from backend.scraper.embeddings import index_segments

# Scrape content
provider = YouTubeProvider()
for source, segments in provider.collect(url="https://www.youtube.com/watch?v=..."):
    # Use existing database connection
    conn = get_db_connection()
    init_db(conn)
    
    # Insert into database
    source_id = insert_source(
        conn,
        source.source_type,
        source.title,
        source.url,
        source.published_at,
    )
    
    # Index with embeddings
    index_segments(conn, source_id, segments, generate_embeddings=True)
    
    conn.close()
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'backend'"

**Solution**: Run commands from the project root directory:
```bash
cd /path/to/contradiction-finder
python -m backend.scraper.run youtube --url ...
```

### Issue: "sentence-transformers not installed"

**Solution**: Install the optional dependency:
```bash
pip install sentence-transformers
```

### Issue: "Robots.txt disallows scraping"

**Solution**: The site's robots.txt file blocks your scraper. This is by design for safety. Choose a different source or contact the site owner.

### Issue: "No transcript available" (YouTube)

**Solution**: Not all YouTube videos have transcripts. Try a different video or use the official API for videos with captions.

### Issue: Rate limit errors

**Solution**: The scraper already includes rate limiting (1 RPS). If you need slower scraping, modify the `max_rps` parameter in provider initialization.

## Customization

### Adjust Rate Limiting

```python
# In providers.py or when creating provider instance
provider = YouTubeProvider(max_rps=0.5)  # 1 request every 2 seconds
```

### Custom User Agent

```python
provider = RSSProvider(user_agent="MyBot/1.0 (contact@example.com)")
```

### Disable robots.txt Checking (Not Recommended)

```python
provider = GenericProvider(allowed_domains=['example.com'], check_robots=False)
```

## Adding New Providers

To add a new content source:

1. **Create Provider Class**

```python
# In backend/scraper/providers.py
class MyNewProvider(Provider):
    def collect(self, url: str, **kwargs):
        # Check robots.txt
        if not self.check_robots_txt(url):
            return
        
        # Rate limit
        self.rate_limiter.wait()
        
        # Fetch and parse content
        response = self.session.get(url)
        # ... parsing logic ...
        
        # Create source and segments
        source = Source(
            source_type='mynewprovider',
            title='...',
            url=url,
            published_at=datetime.now(),
        )
        
        segments = [
            Segment(text='...', meta_json={'key': 'value'})
        ]
        
        yield source, segments
```

2. **Add CLI Command**

```python
# In backend/scraper/run.py
def scrape_mynewprovider(args):
    provider = MyNewProvider()
    # ... implementation ...

# In main() function
mynew_parser = subparsers.add_parser('mynewprovider', help='Scrape My New Source')
mynew_parser.add_argument('--url', type=str, required=True)
mynew_parser.set_defaults(func=scrape_mynewprovider)
```

3. **Add Tests**

```python
# In tests/test_scraper.py
class TestMyNewProvider(unittest.TestCase):
    def test_collect(self):
        provider = MyNewProvider()
        results = list(provider.collect(url='https://example.com'))
        self.assertGreater(len(results), 0)
```

## Best Practices

1. **Always Test in Dry-Run First**: Use the scraper without `--commit` to preview results

2. **Set Contact Email**: Always set `SCRAPER_CONTACT` environment variable for ethical scraping

3. **Respect Rate Limits**: Don't decrease `max_rps` below 0.5 unless you have permission

4. **Check robots.txt**: Don't disable robots.txt checking unless absolutely necessary

5. **Use Embeddings Wisely**: Embedding generation is CPU/GPU intensive. Use `--embed` flag only when needed

6. **Monitor Storage**: Raw text files and embeddings can use significant disk space

7. **Backup Database**: Regularly backup your SQLite database

## Performance Tips

1. **Batch Processing**: Process multiple sources in a single run when possible

2. **Embeddings**: Generate embeddings in batches after scraping multiple sources:
   ```bash
   # Scrape without embeddings
   python -m backend.scraper.run rss --url FEED_URL --commit
   
   # Generate embeddings later in batch
   python -c "from backend.scraper.db import get_db_connection; from backend.scraper.embeddings import embed_segments; conn = get_db_connection(); embed_segments(conn); conn.close()"
   ```

3. **GPU Acceleration**: If you have a CUDA-capable GPU, install PyTorch with CUDA support for faster embedding generation

## Security Considerations

1. **Input Validation**: All URLs are validated before scraping

2. **Domain Whitelisting**: Generic provider requires explicit domain whitelist

3. **No Authentication**: The scraper doesn't support authenticated access (by design for safety)

4. **Local Storage Only**: All data stays on your local machine

5. **No Headless Browsers**: Uses simple HTTP requests only (no JavaScript execution)

## License Compliance

Ensure you comply with:
- Terms of service of scraped websites
- robots.txt directives
- Copyright and fair use laws
- Data protection regulations (GDPR, etc.)

This scraper is designed for research and analysis purposes. Always respect content licensing and terms of use.
'''

# Write implementation guide
with open('IMPLEMENTATION_GUIDE.md', 'w', encoding='utf-8') as f:
    f.write(implementation_guide)

print("Created IMPLEMENTATION_GUIDE.md")
print(f"Guide length: {len(implementation_guide)} characters")
