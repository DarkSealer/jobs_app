"""User profile model for job matching."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Skill:
    """Represents a technical skill."""
    name: str
    proficiency_level: int = 3  # 1-5 scale
    years_experience: float = 0.0
    
    def __str__(self) -> str:
        return f"{self.name} ({self.years_experience}y)"


@dataclass
class Project:
    """Represents a project you've built."""
    name: str
    description: str
    technologies: List[str] = field(default_factory=list)
    url: Optional[str] = None
    
    def get_technologies_set(self) -> set:
        """Get technologies as a set for matching."""
        return set(tech.lower() for tech in self.technologies)
    
    def __str__(self) -> str:
        return f"{self.name}: {', '.join(self.technologies)}"


@dataclass
class UserProfile:
    """Represents the user's professional profile."""
    
    name: str
    email: str
    description: str
    experience_years: int
    skills: List[Skill] = field(default_factory=list)
    job_titles: List[str] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    
    def get_skills_list(self) -> List[str]:
        """Get list of skill names."""
        return [skill.name for skill in self.skills]
    
    def get_skills_set(self) -> set:
        """Get lowercase set of skills for matching."""
        return set(skill.name.lower() for skill in self.skills)
    
    def get_all_technologies(self) -> set:
        """Get all technologies from skills and projects."""
        techs = self.get_skills_set()
        for project in self.projects:
            techs.update(project.get_technologies_set())
        return techs
    
    def get_preferred_titles(self) -> List[str]:
        """Get list of preferred job titles."""
        return self.job_titles if self.job_titles else [
            "Software Engineer",
            "Senior Software Engineer",
            "Full Stack Developer",
        ]
    
    @classmethod
    def from_config(cls, config: dict) -> "UserProfile":
        """Create UserProfile from configuration dictionary."""
        profile_data = config.get("profile", {})
        
        # Parse skills
        skills = []
        for skill_name in profile_data.get("skills", []):
            if isinstance(skill_name, str):
                skills.append(Skill(name=skill_name))
            elif isinstance(skill_name, dict):
                skills.append(Skill(**skill_name))
        
        # Parse projects
        projects = []
        for project_data in profile_data.get("projects", []):
            projects.append(Project(**project_data))
        
        return cls(
            name=profile_data.get("name", "Unknown"),
            email=profile_data.get("email", ""),
            description=profile_data.get("description", ""),
            experience_years=profile_data.get("experience_years", 0),
            skills=skills,
            job_titles=profile_data.get("job_titles", []),
            projects=projects,
        )
    
    def __str__(self) -> str:
        return f"{self.name} - {self.experience_years} years experience"
