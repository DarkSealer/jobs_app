"""Base scraper class for job boards."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import time
import random

from ..models.job import Job


class BaseScraper(ABC):
    """Abstract base class for job board scrapers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scraper.
        
        Args:
            config: Scraper-specific configuration
        """
        self.config = config or {}
        self.session = None
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0
    
    @abstractmethod
    def search(
        self, 
        query: str, 
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50
    ) -> List[Job]:
        """
        Search for jobs on the job board.
        
        Args:
            query: Job search query (e.g., "Software Engineer")
            location: Location to search in
            remote: Whether to include remote jobs
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_url: str) -> Optional[Job]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Job object with full details, or None if failed
        """
        pass
    
    def _rate_limit(self):
        """Apply rate limiting to avoid being blocked."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _random_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters that might cause issues
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        return text.strip()
    
    def _extract_salary(self, text: str) -> Optional[str]:
        """Extract salary information from text."""
        import re
        
        if not text:
            return None
        
        # Common salary patterns
        patterns = [
            r'\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?(?:\s*/\s*(?:year|yr|hour|hr))?',
            r'USD\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?',
            r'[\d,]+k(?:\s*[-–]\s*[\d,]+k)?',
            r'salary:\s*\$?[\d,]+(?:\s*[-–]\s*[\d,]+)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_experience_level(self, text: str) -> Optional[str]:
        """Extract experience level from text."""
        if not text:
            return None
        
        text_lower = text.lower()
        
        if any(term in text_lower for term in ["entry level", "junior", "associate"]):
            return "junior"
        elif any(term in text_lower for term in ["mid", "middle", "intermediate"]):
            return "mid-level"
        elif any(term in text_lower for term in ["senior", "sr.", "sr "]):
            return "senior"
        elif any(term in text_lower for term in ["lead", "principal", "staff"]):
            return "lead"
        
        return None
    
    def _extract_job_type(self, text: str) -> Optional[str]:
        """Extract job type from text."""
        if not text:
            return None
        
        text_lower = text.lower()
        
        if "full-time" in text_lower or "full time" in text_lower:
            return "full-time"
        elif "part-time" in text_lower or "part time" in text_lower:
            return "part-time"
        elif "contract" in text_lower or "contractor" in text_lower:
            return "contract"
        elif "internship" in text_lower or "intern" in text_lower:
            return "internship"
        
        return None
    
    def close(self):
        """Close any open connections or sessions."""
        if self.session:
            self.session.close()
