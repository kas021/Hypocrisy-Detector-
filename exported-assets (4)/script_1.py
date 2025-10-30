
# File 2: backend/scraper/providers.py (Part 2 - Provider implementations)
providers_part2 = '''

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
            r'(?:watch\\?v=)([0-9A-Za-z_-]{11})',
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
            sentences = re.split(r'(?<=[.!?])\\s+', text)
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
'''

providers_part3 = '''

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
            sections = re.split(r'\\n#{1,3}\\s+', text)
            segments = []
            
            for idx, section in enumerate(sections):
                section = section.strip()
                if section:
                    # Further split long sections
                    if len(section) > 500:
                        paragraphs = section.split('\\n\\n')
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
        match = re.search(r'wikipedia\\.org/wiki/([^#?]+)', url)
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
'''

print("Generated providers part 2 and 3")
print(f"Providers part 2 length: {len(providers_part2)}")
print(f"Providers part 3 length: {len(providers_part3)}")
