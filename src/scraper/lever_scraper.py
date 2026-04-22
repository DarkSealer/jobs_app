"""Scraper for Lever job boards."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class LeverScraper(BaseScraper):
    """Scraper for Lever-hosted job boards."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
        # Common companies using Lever
        self.company_boards = config.get("company_boards", []) if config else []
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """Search for jobs on Lever boards."""
        jobs = []
        
        if not self.company_boards:
            # Default list of popular tech companies using Lever
            self.company_boards = [
                "coursera", "twitch", "grammarly", "fiverr", "upwork",
                "canva", "affirm", "brex", "ramp", "mercury"
            ]
        
        for company_board in self.company_boards:
            if len(jobs) >= limit:
                break
            
            board_url = f"https://api.lever.co/v0/postings/{company_board}"
            
            try:
                self._rate_limit()
                response = self.session.get(board_url, timeout=15)
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                for posting in data:
                    if len(jobs) >= limit:
                        break
                    
                    title = self._clean_text(posting.get("text", ""))
                    
                    # Filter by query
                    if query and query.lower() not in title.lower():
                        continue
                    
                    url = posting.get("hostedUrl", "")
                    categories = posting.get("categories", {})
                    department = categories.get("department", "")
                    location_data = categories.get("location", "")
                    
                    is_remote = "remote" in str(location_data).lower() or remote
                    
                    jobs.append(Job(
                        title=title,
                        company=company_board.title(),
                        location=str(location_data),
                        description="",
                        source=JobSource.LEVER,
                        url=url,
                        remote=is_remote,
                    ))
                    
            except Exception as e:
                print(f"Error searching Lever board {company_board}: {e}")
        
        return jobs[:limit]
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Lever."""
        try:
            self._rate_limit()
            response = self.session.get(job_url, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_elem = soup.find('h1', attrs={'app': 'title'})
            title = self._clean_text(title_elem.get_text()) if title_elem else ""
            
            content_elem = soup.find('div', class_='posting-content')
            description = self._clean_text(content_elem.get_text()) if content_elem else ""
            
            # Extract company from URL
            parts = job_url.split('/')
            company = "Unknown"
            for i, part in enumerate(parts):
                if 'lever.co' in part and i + 1 < len(parts):
                    company = parts[i + 1].title()
            
            return Job(
                title=title,
                company=company,
                location="Unknown",
                description=description,
                source=JobSource.LEVER,
                url=job_url,
                remote=False,
            )
        except Exception as e:
            print(f"Error parsing Lever job detail: {e}")
            return None
