"""Scraper for Upwork freelance jobs."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class UpworkScraper(BaseScraper):
    """Scraper for Upwork freelance job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://www.upwork.com"
        self.api_url = f"{self.base_url}/api/graphql"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })
        print("ℹ️  Upwork requires authentication for full access to job listings.")
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """Search for jobs on Upwork."""
        jobs = []
        
        # Upwork requires login to view most job details
        # This is a placeholder implementation
        print(f"ℹ️  Upwork search requires authentication: {query}")
        
        try:
            # Try to search public RSS feed as fallback
            rss_url = f"https://www.upwork.com/ab/feed/topics/rss?q={query}&sort=recency&user_timezone=Europe%2FBucharest"
            
            self._rate_limit()
            response = self.session.get(rss_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')[:limit]
                
                for item in items:
                    job = self._parse_rss_item(item)
                    if job:
                        jobs.append(job)
                        
        except Exception as e:
            print(f"Error searching Upwork: {e}")
        
        return jobs
    
    def _parse_rss_item(self, item) -> Optional[Job]:
        """Parse a job from Upwork RSS feed."""
        try:
            title_elem = item.find('title')
            title = self._clean_text(title_elem.get_text()) if title_elem else ""
            
            link_elem = item.find('link')
            url = self._clean_text(link_elem.get_text()) if link_elem else ""
            
            description_elem = item.find('description')
            description = self._clean_text(description_elem.get_text()) if description_elem else ""
            
            pub_date_str = item.find('pubDate')
            posted_date = None
            if pub_date_str:
                try:
                    posted_date = datetime.strptime(pub_date_str.get_text(), "%a, %d %b %Y %H:%M:%S %z")
                except:
                    pass
            
            # Extract budget if available
            budget = self._extract_budget(description)
            
            return Job(
                title=title,
                company="Upwork Client",
                location="Remote",
                description=description,
                source=JobSource.UPWORK,
                url=url,
                posted_date=posted_date,
                salary_range=budget,
                remote=True,
                job_type="contract",
            )
        except Exception as e:
            print(f"Error parsing Upwork job: {e}")
            return None
    
    def _extract_budget(self, description: str) -> Optional[str]:
        """Extract budget information from description."""
        import re
        
        patterns = [
            r'\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?',
            r'Budget:\s*\$[\d,]+',
            r'Fixed-price:\s*\$[\d,]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Upwork."""
        # Upwork requires authentication for detailed job info
        return None
