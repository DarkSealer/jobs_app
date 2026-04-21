"""Job model representing a job posting."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class JobSource(Enum):
    """Enum for job board sources."""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    STACKOVERFLOW = "stackoverflow"
    GITHUB_JOBS = "github_jobs"
    OTHER = "other"


@dataclass
class Job:
    """Represents a job posting."""
    
    title: str
    company: str
    location: str
    description: str
    source: JobSource
    url: str
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # full-time, contract, etc.
    experience_level: Optional[str] = None  # junior, mid, senior
    remote: bool = False
    skills_found: List[str] = field(default_factory=list)
    raw_html: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate and process the job data."""
        if isinstance(self.source, str):
            self.source = JobSource(self.source.lower())
        
        # Detect if remote from location or description
        if not self.remote:
            remote_keywords = ["remote", "work from home", "wfh", "distributed"]
            location_lower = self.location.lower() if self.location else ""
            desc_lower = self.description.lower() if self.description else ""
            
            if any(keyword in location_lower or keyword in desc_lower 
                   for keyword in remote_keywords):
                self.remote = True
    
    def to_dict(self) -> dict:
        """Convert job to dictionary."""
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "source": self.source.value,
            "url": self.url,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "salary_range": self.salary_range,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "remote": self.remote,
            "skills_found": self.skills_found,
            "scraped_at": self.scraped_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create Job from dictionary."""
        if "source" in data and isinstance(data["source"], str):
            data["source"] = JobSource(data["source"])
        if "posted_date" in data and isinstance(data["posted_date"], str):
            data["posted_date"] = datetime.fromisoformat(data["posted_date"])
        if "scraped_at" in data and isinstance(data["scraped_at"], str):
            data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the job."""
        remote_str = "🏠 Remote" if self.remote else f"📍 {self.location}"
        return f"{self.title} at {self.company} | {remote_str}"
