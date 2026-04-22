"""Scraper for Built In job board."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class BuiltInScraper(BaseScraper):
    """Scraper for Built In job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://builtin.com"
        self.search_url = f"{self.base_url}/job/export"
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
        """Search for jobs on Built In."""
        jobs = []
        
        try:
            # Built In has multiple city-specific sites
            # We'll search the main site and common tech hubs
            cities = ["", "austin", "boston", "chicago", "colorado", "la", "ny", "seattle", "sf"]
            
            for city in cities:
                if len(jobs) >= limit:
                    break
                    
                search_url = f"{self.base_url}/{city}jobs" if city else f"{self.base_url}/jobs"
                
                params = {
                    "search-term": query,
                }
                
                if remote:
                    params["f5[0]"] = "Remote"
                
                self._rate_limit()
                response = self.session.get(search_url, params=params, timeout=15)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='node-job-search-result')
                
                for card in job_cards[:limit - len(jobs)]:
                    job = self._parse_job_card(card, query)
                    if job:
                        jobs.append(job)
                
        except Exception as e:
            print(f"Error searching Built In: {e}")
        
        return jobs[:limit]
    
    def _parse_job_card(self, card, query: str) -> Optional[Job]:
        """Parse a job card from Built In."""
        try:
            title_elem = card.find('h3', class_='node-job-search-result__title')
            if not title_elem:
                return None
            
            title = self._clean_text(title_elem.get_text())
            
            # Filter by query
            if query and query.lower() not in title.lower():
                return None
            
            link_elem = title_elem.find('a')
            url = self.base_url + link_elem.get('href', '') if link_elem else ""
            
            company_elem = card.find('h4', class_='node-job-search-result__company-name')
            company = self._clean_text(company_elem.get_text()) if company_elem else "Unknown"
            
            location_elem = card.find('span', class_='node-job-search-result__location')
            location = self._clean_text(location_elem.get_text()) if location_elem else "Unknown"
            
            is_remote = "remote" in location.lower()
            
            return Job(
                title=title,
                company=company,
                location=location,
                description="",
                source=JobSource.BUILT_IN,
                url=url,
                remote=is_remote,
            )
        except Exception as e:
            print(f"Error parsing Built In job: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Built In."""
        return None
