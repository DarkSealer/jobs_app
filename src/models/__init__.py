"""Data models for the job search agent."""

from .job import Job, JobSource
from .profile import UserProfile, Project, Skill
from .match_result import MatchResult, MatchScore

__all__ = [
    "Job",
    "JobSource", 
    "UserProfile",
    "Project",
    "Skill",
    "MatchResult",
    "MatchScore",
]
