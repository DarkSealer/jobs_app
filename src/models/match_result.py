"""Match result model for job-profile matching."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from .job import Job


@dataclass
class MatchScore:
    """Represents the match score breakdown."""
    
    overall_score: float = 0.0  # 0-100
    skills_match: float = 0.0  # 0-100
    experience_match: float = 0.0  # 0-100
    title_match: float = 0.0  # 0-100
    project_relevance: float = 0.0  # 0-100
    
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    
    def get_grade(self) -> str:
        """Get letter grade based on overall score."""
        if self.overall_score >= 90:
            return "A+"
        elif self.overall_score >= 80:
            return "A"
        elif self.overall_score >= 70:
            return "B"
        elif self.overall_score >= 60:
            return "C"
        elif self.overall_score >= 50:
            return "D"
        else:
            return "F"
    
    def __str__(self) -> str:
        return f"{self.overall_score:.1f}% ({self.get_grade()})"


@dataclass
class MatchResult:
    """Represents the result of matching a job to a profile."""
    
    job: Job
    score: MatchScore
    recommendation: str = ""
    notes: List[str] = field(default_factory=list)
    matched_at: datetime = field(default_factory=datetime.now)
    
    def is_good_match(self, threshold: float = 60.0) -> bool:
        """Check if this is a good match based on threshold."""
        return self.score.overall_score >= threshold
    
    def get_summary(self) -> Dict:
        """Get a summary dictionary."""
        return {
            "job_title": self.job.title,
            "company": self.job.company,
            "location": self.job.location,
            "remote": self.job.remote,
            "overall_score": self.score.overall_score,
            "grade": self.score.get_grade(),
            "matched_skills": self.score.matched_skills,
            "missing_skills": self.score.missing_skills,
            "recommendation": self.recommendation,
            "url": self.job.url,
        }
    
    def __str__(self) -> str:
        remote_icon = "🏠" if self.job.remote else "📍"
        return (
            f"{self.job.title} at {self.job.company}\n"
            f"{remote_icon} {self.job.location} | Score: {self.score}\n"
            f"✅ Matched: {', '.join(self.score.matched_skills[:5])}\n"
            f"❌ Missing: {', '.join(self.score.missing_skills[:5])}\n"
            f"💡 {self.recommendation}"
        )
