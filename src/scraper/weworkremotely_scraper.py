"""Scraper for We Work Remotely jobs."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for We Work Remotely job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://weworkremotely.com"
        self.api_url = f"{self.base_url}/remote-jobs-in-programming-dev-and-tech.xml"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """Search for jobs on We Work Remotely."""
        jobs = []
        
        try:
            self._rate_limit()
            response = self.session.get(self.api_url, timeout=15)
            
            if response.status_code != 200:
                print(f"We Work Remotely returned status code: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')[:limit]
            
            for item in items:
                job = self._parse_job_item(item, query)
                if job:
                    jobs.append(job)
            
        except Exception as e:
            print(f"Error searching We Work Remotely: {e}")
        
        return jobs
    
    def _parse_job_item(self, item, query: str) -> Optional[Job]:
        """Parse a job item from RSS feed."""
        try:
            title = self._clean_text(item.find('title').get_text() if item.find('title') else "")
            link = self._clean_text(item.find('link').get_text() if item.find('link') else "")
            description = self._clean_text(item.find('description').get_text() if item.find('description') else "")
            pub_date_str = item.find('pubDate').get_text() if item.find('pubDate') else None
            
            posted_date = None
            if pub_date_str:
                try:
                    posted_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                except:
                    pass
            
            # Filter by query if provided
            if query and query.lower() not in title.lower() and query.lower() not in description.lower():
                return None
            
            return Job(
                title=title,
                company="Unknown",
                location="Remote",
                description=description,
                source=JobSource.WE_WORK_REMOTELY,
                url=link,
                posted_date=posted_date,
                remote=True,
            )
        except Exception as e:
            print(f"Error parsing We Work Remotely job: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from We Work Remotely."""
        return None
