
# First, let's create a comprehensive scraper module structure
# I'll generate all the required files

# File 1: backend/scraper/__init__.py
init_content = '''"""
Scraper module for contradiction-finder.

Provides pluggable providers for scraping content from various sources
while respecting robots.txt and site terms of service.
"""

from .providers import (
    Provider,
    YouTubeProvider,
    RSSProvider,
    WikipediaProvider,
    GovUkProvider,
    HansardProvider,
    GenericProvider,
)

__all__ = [
    "Provider",
    "YouTubeProvider",
    "RSSProvider",
    "WikipediaProvider",
    "GovUkProvider",
    "HansardProvider",
    "GenericProvider",
]
'''

# File 2: backend/scraper/providers.py (Part 1)
providers_part1 = '''"""
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
'''

# Save progress
print("Generated init and providers part 1")
print(f"Init content length: {len(init_content)}")
print(f"Providers part 1 length: {len(providers_part1)}")
