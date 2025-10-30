
# File 6: requirements.txt additions
requirements_additions = '''
# Scraper dependencies
requests>=2.31.0
feedparser>=6.0.10
trafilatura>=1.6.0
youtube-transcript-api>=0.6.1
yt-dlp>=2023.11.0
sentence-transformers>=2.2.0
'''

# File 7: tests/test_scraper.py
test_scraper_content = '''"""
Unit tests for scraper module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from urllib.robotparser import RobotFileParser

from backend.scraper.providers import (
    RobotsChecker,
    RateLimiter,
    YouTubeProvider,
    RSSProvider,
    WikipediaProvider,
)


class TestRobotsChecker(unittest.TestCase):
    """Test robots.txt compliance checking."""
    
    def test_robots_allow(self):
        """Test that allowed URLs pass."""
        checker = RobotsChecker('TestBot/1.0')
        
        # Mock robots.txt content that allows everything
        sample_robots = """
User-agent: *
Allow: /
"""
        
        with patch.object(RobotFileParser, 'read') as mock_read:
            mock_read.return_value = None
            with patch.object(RobotFileParser, 'can_fetch', return_value=True):
                result = checker.can_fetch('https://example.com/page')
                self.assertTrue(result)
    
    def test_robots_deny(self):
        """Test that disallowed URLs are blocked."""
        checker = RobotsChecker('TestBot/1.0')
        
        with patch.object(RobotFileParser, 'read') as mock_read:
            mock_read.return_value = None
            with patch.object(RobotFileParser, 'can_fetch', return_value=False):
                result = checker.can_fetch('https://example.com/private')
                self.assertFalse(result)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting."""
    
    def test_rate_limit_delay(self):
        """Test that rate limiter adds delay."""
        limiter = RateLimiter(max_rps=10, random_delay=False)
        
        import time
        start = time.time()
        limiter.wait()
        limiter.wait()
        elapsed = time.time() - start
        
        # Should take at least min_delay
        self.assertGreaterEqual(elapsed, limiter.min_delay * 0.9)


class TestYouTubeProvider(unittest.TestCase):
    """Test YouTube provider."""
    
    def test_extract_video_id_from_url(self):
        """Test video ID extraction from various URL formats."""
        provider = YouTubeProvider()
        
        test_cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ]
        
        for url, expected_id in test_cases:
            video_id = provider._extract_video_id(url)
            self.assertEqual(video_id, expected_id, f"Failed for URL: {url}")
    
    @patch('backend.scraper.providers.YouTubeTranscriptApi')
    @patch('backend.scraper.providers.yt_dlp.YoutubeDL')
    def test_collect_youtube(self, mock_ytdlp, mock_transcript_api):
        """Test collecting YouTube transcript."""
        # Mock metadata
        mock_ytdlp.return_value.__enter__.return_value.extract_info.return_value = {
            'title': 'Test Video',
            'upload_date': '20231001',
        }
        
        # Mock transcript
        mock_transcript_api.get_transcript.return_value = [
            {'start': 0.0, 'duration': 2.0, 'text': 'Hello'},
            {'start': 2.0, 'duration': 2.0, 'text': 'World'},
        ]
        
        provider = YouTubeProvider()
        results = list(provider.collect(video_id='test123'))
        
        self.assertEqual(len(results), 1)
        source, segments = results[0]
        self.assertEqual(source.source_type, 'youtube')
        self.assertEqual(len(segments), 2)


class TestRSSProvider(unittest.TestCase):
    """Test RSS provider."""
    
    @patch('backend.scraper.providers.feedparser.parse')
    @patch('backend.scraper.providers.trafilatura.fetch_url')
    @patch('backend.scraper.providers.trafilatura.extract')
    def test_collect_rss(self, mock_extract, mock_fetch, mock_parse):
        """Test collecting from RSS feed."""
        # Mock feed
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[
                {
                    'title': 'Test Article',
                    'link': 'https://example.com/article',
                    'published_parsed': (2023, 10, 1, 0, 0, 0, 0, 0, 0),
                }
            ]
        )
        
        # Mock article extraction
        mock_fetch.return_value = '<html>Test content</html>'
        mock_extract.return_value = 'This is a test article. It has multiple sentences.'
        
        provider = RSSProvider(check_robots=False)
        results = list(provider.collect(url='https://example.com/feed'))
        
        self.assertGreater(len(results), 0)


class TestWikipediaProvider(unittest.TestCase):
    """Test Wikipedia provider."""
    
    def test_extract_page_title(self):
        """Test extracting page title from URL."""
        provider = WikipediaProvider()
        
        url = 'https://en.wikipedia.org/wiki/Artificial_intelligence'
        title = provider._extract_page_title(url)
        
        self.assertEqual(title, 'Artificial_intelligence')


if __name__ == '__main__':
    unittest.main()
'''

print("Generated requirements additions and test file")
print(f"Requirements additions length: {len(requirements_additions)}")
print(f"Test content length: {len(test_scraper_content)}")
