"""Scraper for Remote OK jobs."""

from typing import List, Optional, Dict, Any
import requests
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class RemoteOkScraper(BaseScraper):
    """Scraper for Remote OK job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_url = "https://remoteok.com/api"
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
        """Search for jobs on Remote OK."""
        jobs = []
        
        try:
            self._rate_limit()
            response = self.session.get(self.api_url, timeout=15)
            
            if response.status_code != 200:
                print(f"Remote OK returned status code: {response.status_code}")
                return []
            
            data = response.json()
            
            for item in data[:limit]:
                # Filter by query if provided
                if query:
                    title = item.get("position", "")
                    tags = item.get("tags", [])
                    tag_names = [tag.get("name", "").lower() for tag in tags]
                    
                    if query.lower() not in title.lower() and query.lower() not in " ".join(tag_names):
                        continue
                
                job = self._parse_job_item(item)
                if job:
                    jobs.append(job)
            
        except Exception as e:
            print(f"Error searching Remote OK: {e}")
        
        return jobs
    
    def _parse_job_item(self, item: Dict[str, Any]) -> Optional[Job]:
        """Parse a job item from Remote OK API."""
        try:
            title = self._clean_text(item.get("position", ""))
            company = self._clean_text(item.get("company", "Unknown"))
            description = self._clean_text(item.get("description", ""))
            url = item.get("url", "")
            
            # Remote OK is all about remote jobs
            location = "Remote"
            
            # Parse posted date
            posted_date = None
            timestamp = item.get("date")
            if timestamp:
                try:
                    posted_date = datetime.fromtimestamp(int(timestamp))
                except:
                    pass
            
            # Extract salary if available
            salary = item.get("salary", "")
            
            return Job(
                title=title,
                company=company,
                location=location,
                description=description,
                source=JobSource.REMOTE_OK,
                url=url,
                posted_date=posted_date,
                salary_range=salary if salary else None,
                remote=True,
            )
        except Exception as e:
            print(f"Error parsing Remote OK job: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Remote OK."""
        return None
