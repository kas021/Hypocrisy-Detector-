"""
Provider classes for different content sources.
Each provider respects robots.txt and implements a common interface.
"""

import time
import random
import re
import logging
import json
from abc import ABC, abstractmethod
from typing import Iterable, List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import os

import requests
import feedparser
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Source:
    """Represents a content source."""

    def __init__(
        self,
        source_type: str,
        title: str,
        url: str,
        published_at: Optional[datetime] = None,
        source_id: Optional[int] = None,
    ):
        self.id = source_id
        self.source_type = source_type
        self.title = title
        self.url = url
        self.published_at = published_at or datetime.now()


class Segment:
    """Represents a text segment from a source."""

    def __init__(
        self,
        text: str,
        ts_start: Optional[float] = None,
        ts_end: Optional[float] = None,
        meta_json: Optional[Dict] = None,
        segment_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ):
        self.id = segment_id
        self.source_id = source_id
        self.text = text
        self.ts_start = ts_start
        self.ts_end = ts_end
        self.meta_json = meta_json or {}


class RobotsChecker:
    """Checks robots.txt compliance."""

    def __init__(self, user_agent: str, max_cache_age: int = 3600):
        self.user_agent = user_agent
        self.max_cache_age = max_cache_age
        self._cache: Dict[str, Tuple[RobotFileParser, float]] = {}

    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        # Check cache
        now = time.time()
        if robots_url in self._cache:
            rp, cached_time = self._cache[robots_url]
            if now - cached_time < self.max_cache_age:
                return self._check_permission(rp, url)

        # Fetch and parse robots.txt
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            rp.read()
            self._cache[robots_url] = (rp, now)
            return self._check_permission(rp, url)
        except Exception as e:
            logger.warning(f"Could not read robots.txt for {robots_url}: {e}")
            # Fail open if robots.txt cannot be read
            return True

    def _check_permission(self, rp: RobotFileParser, url: str) -> bool:
        """Check if user agent can fetch URL."""
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt permission: {e}")
            return True


class RateLimiter:
    """Rate limiter for polite scraping."""

    def __init__(self, max_rps: float = 1.0, random_delay: bool = True):
        self.max_rps = max_rps
        self.random_delay = random_delay
        self.min_delay = 1.0 / max_rps
        self._last_request = 0.0

    def wait(self):
        """Wait to respect rate limit."""
        now = time.time()
        elapsed = now - self._last_request

        if elapsed < self.min_delay:
            delay = self.min_delay - elapsed
            if self.random_delay:
                delay += random.uniform(0, self.min_delay * 0.5)
            time.sleep(delay)

        self._last_request = time.time()


class Provider(ABC):
    """Base class for content providers."""

    def __init__(
        self,
        user_agent: Optional[str] = None,
        max_rps: float = 1.0,
        check_robots: bool = True,
    ):
        contact = os.environ.get("SCRAPER_CONTACT", "your-email@example.com")
        self.user_agent = user_agent or f"ContradictionFinder/1.0 ({contact})"
        self.robots_checker = RobotsChecker(self.user_agent) if check_robots else None
        self.rate_limiter = RateLimiter(max_rps=max_rps)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def check_robots_txt(self, url: str) -> bool:
        """Check if URL can be scraped according to robots.txt."""
        if not self.robots_checker:
            return True

        allowed = self.robots_checker.can_fetch(url)
        if not allowed:
            logger.warning(f"Robots.txt disallows scraping: {url}")
        return allowed

    @abstractmethod
    def collect(self, **kwargs) -> Iterable[Tuple[Source, List[Segment]]]:
        """Collect content from the provider."""
        pass


class YouTubeProvider(Provider):
    """Provider for YouTube video transcripts."""

    def collect(
        self,
        url: Optional[str] = None,
        video_id: Optional[str] = None,
        **kwargs
    ) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect YouTube transcript.

        Args:
            url: YouTube video URL
            video_id: YouTube video ID (alternative to url)
        """
        if not video_id and not url:
            raise ValueError("Either url or video_id must be provided")

        # Extract video ID from URL if needed
        if url and not video_id:
            video_id = self._extract_video_id(url)
            if not video_id:
                logger.error(f"Could not extract video ID from URL: {url}")
                return

        # YouTube allows transcript API access
        try:
            # Get metadata using yt-dlp (no download)
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False
                )

            # Get transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Create source
            published_at = None
            if 'upload_date' in info:
                try:
                    published_at = datetime.strptime(info['upload_date'], '%Y%m%d')
                except:
                    pass

            source = Source(
                source_type='youtube',
                title=info.get('title', f'YouTube video {video_id}'),
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=published_at,
            )

            # Create segments from transcript
            segments = []
            for entry in transcript:
                segment = Segment(
                    text=entry['text'],
                    ts_start=entry['start'],
                    ts_end=entry['start'] + entry.get('duration', 0),
                    meta_json={'video_id': video_id}
                )
                segments.append(segment)

            yield source, segments

        except Exception as e:
            logger.error(f"Error collecting YouTube transcript for {video_id}: {e}")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None


class RSSProvider(Provider):
    """Provider for RSS/Atom feeds."""

    def collect(self, url: str, **kwargs) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect items from RSS/Atom feed.

        Args:
            url: Feed URL
        """
        try:
            # Parse feed
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                logger.error(f"Failed to parse feed: {url}")
                return

            # Process each entry
            for entry in feed.entries:
                self.rate_limiter.wait()

                article_url = entry.get('link', '')
                if not article_url:
                    continue

                # Check robots.txt
                if not self.check_robots_txt(article_url):
                    continue

                # Get published date
                published_at = None
                for date_field in ['published_parsed', 'updated_parsed']:
                    if date_field in entry and entry[date_field]:
                        try:
                            published_at = datetime(*entry[date_field][:6])
                            break
                        except:
                            pass

                # Create source
                source = Source(
                    source_type='rss',
                    title=entry.get('title', 'Untitled'),
                    url=article_url,
                    published_at=published_at,
                )

                # Fetch and extract article content
                segments = self._extract_article_segments(article_url)

                if segments:
                    yield source, segments

        except Exception as e:
            logger.error(f"Error collecting RSS feed {url}: {e}")

    def _extract_article_segments(self, url: str) -> List[Segment]:
        """Extract article content and split into segments."""
        try:
            # Download page
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return []

            # Extract main text
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
            )

            if not text:
                return []

            # Split into segments (1-3 sentences each)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            segments = []

            for i in range(0, len(sentences), 2):
                segment_text = ' '.join(sentences[i:i+3])
                if segment_text.strip():
                    segment = Segment(
                        text=segment_text.strip(),
                        meta_json={'url': url, 'sentence_range': f"{i}-{i+3}"}
                    )
                    segments.append(segment)

            return segments

        except Exception as e:
            logger.error(f"Error extracting article {url}: {e}")
            return []


class WikipediaProvider(Provider):
    """Provider for Wikipedia articles via REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base = "https://en.wikipedia.org/w/rest.php/v1"

    def collect(
        self,
        page: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs
    ) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect Wikipedia article content.

        Args:
            page: Page title
            url: Wikipedia URL (alternative to page)
        """
        if not page and not url:
            raise ValueError("Either page or url must be provided")

        # Extract page title from URL if needed
        if url and not page:
            page = self._extract_page_title(url)
            if not page:
                logger.error(f"Could not extract page title from URL: {url}")
                return

        try:
            # Fetch page content
            page_url = f"{self.api_base}/page/{page}/html"

            self.rate_limiter.wait()
            response = self.session.get(page_url)
            response.raise_for_status()

            html_content = response.text

            # Extract text using trafilatura
            text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
            )

            if not text:
                logger.error(f"No content extracted from Wikipedia page: {page}")
                return

            # Create source
            source = Source(
                source_type='wikipedia',
                title=page.replace('_', ' '),
                url=f"https://en.wikipedia.org/wiki/{page}",
                published_at=datetime.now(),
            )

            # Split by sections (simple heuristic)
            sections = re.split(r'\n#{1,3}\s+', text)
            segments = []

            for idx, section in enumerate(sections):
                section = section.strip()
                if section:
                    # Further split long sections
                    if len(section) > 500:
                        paragraphs = section.split('\n\n')
                        for para in paragraphs:
                            if para.strip():
                                segment = Segment(
                                    text=para.strip(),
                                    meta_json={'page': page, 'section_idx': idx}
                                )
                                segments.append(segment)
                    else:
                        segment = Segment(
                            text=section,
                            meta_json={'page': page, 'section_idx': idx}
                        )
                        segments.append(segment)

            yield source, segments

        except Exception as e:
            logger.error(f"Error collecting Wikipedia page {page}: {e}")

    def _extract_page_title(self, url: str) -> Optional[str]:
        """Extract page title from Wikipedia URL."""
        match = re.search(r'wikipedia\.org/wiki/([^#?]+)', url)
        if match:
            return match.group(1)
        return None


class GovUkProvider(RSSProvider):
    """Provider for GOV.UK publications via RSS."""

    def collect(self, url: str, **kwargs) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect GOV.UK content from RSS feed.

        Args:
            url: GOV.UK RSS feed URL
        """
        # Validate it's a gov.uk domain
        parsed = urlparse(url)
        if 'gov.uk' not in parsed.netloc:
            logger.warning(f"URL does not appear to be from gov.uk: {url}")

        # Use parent RSS implementation
        for source, segments in super().collect(url, **kwargs):
            # Update source type
            source.source_type = 'govuk'
            yield source, segments


class HansardProvider(Provider):
    """Provider for UK Parliament Hansard debates."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base = "https://hansard-api.parliament.uk"

    def collect(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs
    ) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect Hansard debate content.

        Args:
            query: Search query keyword
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        """
        try:
            # Build API request
            params = {
                'searchTerm': query,
                'take': 20,
            }

            if from_date:
                params['startDate'] = from_date
            if to_date:
                params['endDate'] = to_date

            # Note: Using a simplified approach since the actual Hansard API
            # structure varies. This would need adjustment based on actual API.
            search_url = f"{self.api_base}/search/debates.json"

            self.rate_limiter.wait()
            response = self.session.get(search_url, params=params)

            # If API is not available, log and return
            if response.status_code != 200:
                logger.warning(
                    f"Hansard API returned status {response.status_code}. "
                    "This provider may need API credentials or adjustments."
                )
                return

            data = response.json()

            # Process results (structure may vary)
            for item in data.get('results', []):
                # Create source
                source = Source(
                    source_type='hansard',
                    title=item.get('title', 'Hansard Debate'),
                    url=item.get('url', ''),
                    published_at=self._parse_date(item.get('date')),
                )

                # Create segment from debate text
                text = item.get('text', '')
                if text:
                    segment = Segment(
                        text=text,
                        meta_json={
                            'speaker': item.get('speaker', ''),
                            'debate_id': item.get('id', ''),
                        }
                    )
                    yield source, [segment]

        except Exception as e:
            logger.error(f"Error collecting Hansard data: {e}")

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None


class GenericProvider(Provider):
    """Provider for generic web pages with domain whitelist."""

    def __init__(self, allowed_domains: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_domains = [d.lower() for d in allowed_domains]

    def collect(self, urls: List[str], **kwargs) -> Iterable[Tuple[Source, List[Segment]]]:
        """
        Collect content from whitelisted domains.

        Args:
            urls: List of URLs to scrape
        """
        for url in urls:
            # Check if domain is whitelisted
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix for comparison
            domain_clean = domain.replace('www.', '')

            allowed = any(
                domain_clean == allowed or domain_clean.endswith('.' + allowed)
                for allowed in self.allowed_domains
            )

            if not allowed:
                logger.warning(
                    f"Domain {domain} not in whitelist. Skipping {url}"
                )
                continue

            # Check robots.txt
            if not self.check_robots_txt(url):
                continue

            try:
                self.rate_limiter.wait()

                # Fetch and extract content
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    logger.warning(f"Could not download {url}")
                    continue

                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                )

                if not text:
                    logger.warning(f"No content extracted from {url}")
                    continue

                # Get metadata
                metadata = trafilatura.extract_metadata(downloaded)

                title = 'Untitled'
                published_at = None

                if metadata:
                    title = metadata.title or title
                    if metadata.date:
                        try:
                            published_at = datetime.fromisoformat(metadata.date)
                        except:
                            pass

                # Create source
                source = Source(
                    source_type='generic',
                    title=title,
                    url=url,
                    published_at=published_at,
                )

                # Split into segments
                paragraphs = text.split('\n\n')
                segments = []

                for para in paragraphs:
                    para = para.strip()
                    if para and len(para) > 50:  # Skip very short paragraphs
                        segment = Segment(
                            text=para,
                            meta_json={'url': url, 'domain': domain}
                        )
                        segments.append(segment)

                if segments:
                    yield source, segments

            except Exception as e:
                logger.error(f"Error collecting from {url}: {e}")
