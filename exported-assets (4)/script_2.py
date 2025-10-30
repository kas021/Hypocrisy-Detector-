
# File 2: backend/scraper/providers.py (Part 4 - Remaining providers)
providers_part4 = '''

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
                paragraphs = text.split('\\n\\n')
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
'''

print("Generated providers part 4")
print(f"Providers part 4 length: {len(providers_part4)}")
