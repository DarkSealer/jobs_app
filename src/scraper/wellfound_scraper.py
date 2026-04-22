"""Scraper for Wellfound (formerly AngelList) jobs."""

from typing import List, Optional, Dict, Any
import requests
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class WellfoundScraper(BaseScraper):
    """Scraper for Wellfound (AngelList) job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://wellfound.com"
        self.api_url = "https://www.wellfound.com/api/jobs"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })
        print("ℹ️  Wellfound may require authentication for full access.")
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """Search for jobs on Wellfound."""
        jobs = []
        
        # Wellfound requires authentication, so we provide a placeholder
        # In production, you would need to use their API with proper auth
        print(f"ℹ️  Wellfound search requires authentication: {query}")
        
        try:
            # Try to fetch public job listings
            params = {
                "query": query,
                "limit": limit,
            }
            
            if remote:
                params["remote"] = "true"
            
            self._rate_limit()
            response = self.session.get(self.api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                job_listings = data.get("jobs", [])
                
                for listing in job_listings[:limit]:
                    job = self._parse_job_listing(listing)
                    if job:
                        jobs.append(job)
        except Exception as e:
            print(f"Error searching Wellfound: {e}")
        
        return jobs
    
    def _parse_job_listing(self, listing: Dict[str, Any]) -> Optional[Job]:
        """Parse a job listing from Wellfound."""
        try:
            title = self._clean_text(listing.get("title", ""))
            company = listing.get("company", {}).get("name", "Unknown")
            description = self._clean_text(listing.get("description", ""))
            url = listing.get("url", "")
            location = self._clean_text(listing.get("location", "Remote"))
            
            is_remote = "remote" in location.lower() or listing.get("remote", False)
            
            return Job(
                title=title,
                company=company,
                location=location,
                description=description,
                source=JobSource.WELLFOUND,
                url=url,
                remote=is_remote,
            )
        except Exception as e:
            print(f"Error parsing Wellfound job: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Wellfound."""
        return None
