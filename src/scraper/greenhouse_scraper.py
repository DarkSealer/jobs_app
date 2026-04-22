"""Scraper for Greenhouse job boards."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse-hosted job boards."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
        # Common companies using Greenhouse
        self.company_boards = config.get("company_boards", []) if config else []
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """Search for jobs on Greenhouse boards."""
        jobs = []
        
        # Greenhouse hosts job boards for many companies
        # You need to specify which company boards to search
        if not self.company_boards:
            # Default list of popular tech companies using Greenhouse
            self.company_boards = [
                "shopify", "stripe", "coinbase", "roblox", "notion",
                "figma", "airtable", "doordash", "instacart", "lyft"
            ]
        
        for company_board in self.company_boards:
            if len(jobs) >= limit:
                break
            
            board_url = f"https://boards.greenhouse.io/{company_board}"
            
            try:
                self._rate_limit()
                response = self.session.get(board_url, timeout=15)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_links = soup.find_all('a', class_='absolute-link')
                
                for link in job_links:
                    if len(jobs) >= limit:
                        break
                    
                    title = self._clean_text(link.get_text())
                    
                    # Filter by query
                    if query and query.lower() not in title.lower():
                        continue
                    
                    href = link.get('href', '')
                    url = f"https://boards.greenhouse.io{href}" if href.startswith('/') else href
                    
                    # Try to get location from parent element
                    location_elem = link.find_parent().find(class_='location')
                    job_location = self._clean_text(location_elem.get_text()) if location_elem else "Unknown"
                    
                    is_remote = "remote" in job_location.lower() or remote
                    
                    jobs.append(Job(
                        title=title,
                        company=company_board.title(),
                        location=job_location,
                        description="",
                        source=JobSource.GREENHOUSE,
                        url=url,
                        remote=is_remote,
                    ))
                    
            except Exception as e:
                print(f"Error searching Greenhouse board {company_board}: {e}")
        
        return jobs[:limit]
    
    def _parse_job_detail(self, url: str, company: str) -> Optional[Job]:
        """Parse job details from a Greenhouse job page."""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_elem = soup.find('h1', attrs={'app': 'title'})
            title = self._clean_text(title_elem.get_text()) if title_elem else ""
            
            content_elem = soup.find('div', id='content')
            description = self._clean_text(content_elem.get_text()) if content_elem else ""
            
            return Job(
                title=title,
                company=company,
                location="Unknown",
                description=description,
                source=JobSource.GREENHOUSE,
                url=url,
                remote=False,
            )
        except Exception as e:
            print(f"Error parsing Greenhouse job detail: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Greenhouse."""
        # Extract company from URL
        parts = job_url.split('/')
        if len(parts) >= 4 and 'greenhouse.io' in job_url:
            company = parts[3]
            return self._parse_job_detail(job_url, company)
        return None
