"""Remotive public API scraper fallback."""

from typing import List, Optional, Dict, Any
from datetime import datetime

import requests

from .base_scraper import BaseScraper
from ..models.job import Job, JobSource


class RemotiveScraper(BaseScraper):
    """Scraper for Remotive jobs public API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = "https://remotive.com/api/remote-jobs"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        remote: bool = False,
        limit: int = 50,
    ) -> List[Job]:
        """
        Search for remote jobs on Remotive.

        Note: Remotive provides remote jobs, so the location parameter is
        intentionally ignored.
        """
        try:
            self._rate_limit()
            response = self.session.get(
                self.base_url,
                params={"search": query},
                timeout=15,
            )

            if response.status_code != 200:
                print(f"Remotive returned status code: {response.status_code}")
                return []

            payload = response.json() or {}
            items = payload.get("jobs", [])[:limit]
            return [job for item in items if (job := self._parse_job(item))]
        except Exception as error:
            print(f"Error searching Remotive: {error}")
            return []

    def get_job_details(self, job_url: str) -> Optional[Job]:
        """Remotive API already returns rich job details in search."""
        return None

    def _parse_job(self, item: Dict[str, Any]) -> Optional[Job]:
        """Convert API job item to internal Job model."""
        try:
            publication_date = item.get("publication_date")
            posted_date = None
            if publication_date:
                posted_date = datetime.fromisoformat(
                    publication_date.replace("Z", "+00:00")
                )

            return Job(
                title=self._clean_text(item.get("title", "")),
                company=self._clean_text(item.get("company_name", "Unknown")),
                location=self._clean_text(
                    item.get("candidate_required_location", "Remote")
                ),
                description=self._clean_text(item.get("description", "")),
                source=JobSource.OTHER,
                url=item.get("url", ""),
                posted_date=posted_date,
                salary_range=self._extract_salary(item.get("salary", "")),
                job_type=self._extract_job_type(item.get("job_type", "")),
                remote=True,
            )
        except Exception as error:
            print(f"Error parsing Remotive job: {error}")
            return None
