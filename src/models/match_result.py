"""Match result model for job-profile matching."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    score_breakdown: Dict[str, Any] = field(default_factory=dict)

    def get_grade(self) -> str:
        """Legacy letter grade based on overall score (CLI / CSV)."""
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

    def get_quality_band(self) -> str:
        """
        Human-readable match tier (GUI).

        Excellent / Strong require at least one matched profile skill
        in the job tech overlap (not LLM-based).
        """
        s = self.overall_score
        has_skill = len(self.matched_skills) > 0
        if s >= 85 and has_skill:
            return "Excellent"
        if s >= 70 and has_skill:
            return "Strong"
        if s >= 55:
            return "Maybe"
        return "Weak"

    def __str__(self) -> str:
        return f"{self.overall_score:.1f}% ({self.get_quality_band()})"


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
            "quality_band": self.score.get_quality_band(),
            "skills_match": self.score.skills_match,
            "experience_match": self.score.experience_match,
            "title_match": self.score.title_match,
            "project_relevance": self.score.project_relevance,
            "matched_skills": self.score.matched_skills,
            "missing_skills": self.score.missing_skills,
            "matched_keywords": self.score.matched_keywords,
            "score_breakdown": self.score.score_breakdown,
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
