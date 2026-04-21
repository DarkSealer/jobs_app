"""Indeed.com job scraper."""

from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com job board."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://www.indeed.com"
        self.search_url = f"{self.base_url}/jobs"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
    
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """
        Search for jobs on Indeed.
        
        Note: This is a demo implementation. Indeed has anti-scraping measures
        and may require using their official API or Playwright/Selenium for
        reliable scraping.
        """
        jobs = []
        start = 0
        results_per_page = 15
        
        while len(jobs) < limit:
            params = {
                "q": query,
                "start": start,
            }
            
            if location and not remote:
                params["l"] = location
            elif remote:
                params["remotejob"] = "1"
                if location:
                    params["l"] = location
            
            try:
                self._rate_limit()
                response = self.session.get(self.search_url, params=params, timeout=10)
                
                if response.status_code != 200:
                    print(f"Indeed returned status code: {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='job_seen_beacon')
                
                if not job_cards:
                    break
                
                for card in job_cards:
                    if len(jobs) >= limit:
                        break
                    
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                
                if len(job_cards) < results_per_page:
                    break
                
                start += results_per_page
                self._random_delay(1, 3)
                
            except Exception as e:
                print(f"Error searching Indeed: {e}")
                break
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a job card from search results."""
        try:
            # Extract job title
            title_elem = card.find('a', attrs={'data-jk': True})
            if not title_elem:
                return None
            
            title = self._clean_text(title_elem.get('title', ''))
            job_url = self.base_url + title_elem.get('href', '')
            job_id = title_elem.get('data-jk', '')
            
            # Extract company
            company_elem = card.find('span', class_='companyName')
            company = self._clean_text(company_elem.get_text()) if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('div', class_='companyLocation')
            location = self._clean_text(location_elem.get_text()) if location_elem else ""
            
            # Extract snippet/description preview
            snippet_elem = card.find('div', class_='job-snippet')
            description_preview = self._clean_text(snippet_elem.get_text()) if snippet_elem else ""
            
            # Extract salary if available
            salary_elem = card.find('div', attrs={'data-testid': 'attribute_snippet_testid'})
            salary = self._clean_text(salary_elem.get_text()) if salary_elem else None
            
            # Check if remote
            is_remote = 'remote' in location.lower() or 'remote' in description_preview.lower()
            
            return Job(
                title=title,
                company=company,
                location=location,
                description=description_preview,
                source=JobSource.INDEED,
                url=job_url,
                salary_range=salary,
                remote=is_remote,
            )
            
        except Exception as e:
            print(f"Error parsing job card: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Get full job details from Indeed."""
        try:
            self._rate_limit()
            response = self.session.get(job_url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract full description
            desc_elem = soup.find('div', id='jobDescriptionText')
            full_description = self._clean_text(desc_elem.get_text()) if desc_elem else ""
            
            # Try to extract posted date
            date_elem = soup.find('span', attrs={'data-testid': 'myJobsStateDate'})
            posted_date = None
            if date_elem:
                date_str = self._clean_text(date_elem.get_text())
                posted_date = self._parse_date(date_str)
            
            # Update the job with full description
            # Note: In a real implementation, you'd fetch the existing job and update it
            return None  # Would need to return updated Job object
            
        except Exception as e:
            print(f"Error getting job details: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from Indeed."""
        if not date_str:
            return None
        
        try:
            # Handle relative dates like "Just posted", "Today", "2 days ago"
            date_str_lower = date_str.lower()
            
            if "just" in date_str_lower or "today" in date_str_lower:
                return datetime.now()
            elif "yesterday" in date_str_lower:
                return datetime.now().replace(day=datetime.now().day - 1)
            elif "days ago" in date_str_lower:
                days_ago = int(date_str_lower.split()[0])
                from datetime import timedelta
                return datetime.now() - timedelta(days=days_ago)
            elif "hours ago" in date_str_lower:
                return datetime.now()
            
            # Try standard date formats
            for fmt in ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
