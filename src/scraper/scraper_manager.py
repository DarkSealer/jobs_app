"""Unified job scraper manager that coordinates multiple job board scrapers."""

from typing import List, Optional, Dict, Any, Type
from datetime import datetime

from .base_scraper import BaseScraper
from ..models.job import Job


class ScraperManager:
    """Manages multiple job board scrapers and aggregates results."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.scrapers: List[BaseScraper] = []
        self.enabled_boards = config.get("job_boards", {}) if config else {}
    
    def register_scraper(self, scraper: BaseScraper):
        """Register a scraper instance."""
        self.scrapers.append(scraper)
    
    def search_all(
        self,
        query: str,
        location: Optional[str] = None,
        remote: bool = False,
        limit_per_board: int = 50,
        verbose: bool = False
    ) -> List[Job]:
        """
        Search all registered scrapers and aggregate results.
        
        Args:
            query: Job search query
            location: Location to search
            remote: Whether to include remote jobs
            limit_per_board: Max jobs per scraper
            verbose: Print progress information
            
        Returns:
            List of all jobs found across all scrapers
        """
        all_jobs = []
        
        for scraper in self.scrapers:
            scraper_name = scraper.__class__.__name__
            
            if verbose:
                print(f"🔎 Searching {scraper_name}...")
            
            try:
                jobs = scraper.search(
                    query=query,
                    location=location,
                    remote=remote,
                    limit=limit_per_board
                )
                
                if verbose:
                    print(f"   ✓ Found {len(jobs)} jobs from {scraper_name}")
                
                all_jobs.extend(jobs)
                
            except Exception as e:
                if verbose:
                    print(f"   ⚠️  Error with {scraper_name}: {e}")
        
        return all_jobs
    
    def remove_duplicates(self, jobs: List[Job]) -> List[Job]:
        """Remove duplicate jobs based on URL or title+company combination."""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique key for each job
            key = job.url or f"{job.source.value}:{job.title}:{job.company}"
            
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def close_all(self):
        """Close all scraper connections."""
        for scraper in self.scrapers:
            try:
                scraper.close()
            except:
                pass
