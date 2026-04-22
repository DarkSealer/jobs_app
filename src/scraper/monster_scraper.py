"""Scraper for Monster jobs."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class MonsterScraper(BaseScraper):
    """Scraper for Monster job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://www.monster.com"
        self.search_url = f"{self.base_url}/jobs/search"
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
        """Search for jobs on Monster."""
        jobs = []
        
        try:
            params = {
                "q": query,
                "where": location or "",
                "pagesize": min(limit, 50),
            }
            
            if remote:
                params["radius"] = 0
            
            self._rate_limit()
            response = self.session.get(self.search_url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"Monster returned status code: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='card-content')
            
            for card in job_cards[:limit]:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            
        except Exception as e:
            print(f"Error searching Monster: {e}")
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a job card from Monster."""
        try:
            title_elem = card.find('h2', class_='title')
            if not title_elem:
                return None
            
            link_elem = title_elem.find('a')
            title = self._clean_text(link_elem.get('title', '')) if link_elem else ""
            url = link_elem.get('href', '') if link_elem else ""
            
            company_elem = card.find('div', class_='company')
            company = self._clean_text(company_elem.get_text()) if company_elem else "Unknown"
            
            location_elem = card.find('div', class_='location')
            location = self._clean_text(location_elem.get_text()) if location_elem else "Unknown"
            
            is_remote = "remote" in location.lower()
            
            return Job(
                title=title,
                company=company,
                location=location,
                description="",
                source=JobSource.MONSTER,
                url=url if url.startswith('http') else f"{self.base_url}{url}",
                remote=is_remote,
            )
        except Exception as e:
            print(f"Error parsing Monster job: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Monster."""
        return None
