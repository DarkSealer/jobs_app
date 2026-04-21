"""Job matcher that compares jobs against user profile."""

from typing import List, Dict, Optional
import re

from ..models.job import Job
from ..models.profile import UserProfile
from ..models.match_result import MatchResult, MatchScore
from .tech_extractor import TechStackExtractor


class JobMatcher:
    """Matches jobs against user profile and calculates match scores."""
    
    def __init__(self, profile: UserProfile, config: Optional[Dict] = None):
        """
        Initialize the job matcher.
        
        Args:
            profile: User's profile with skills and experience
            config: Optional configuration for matching weights
        """
        self.profile = profile
        self.config = config or {}
        self.tech_extractor = TechStackExtractor()
        
        # Get matching weights from config
        matching_config = self.config.get("matching", {})
        self.skills_weight = matching_config.get("skills_weight", 0.5)
        self.experience_weight = matching_config.get("experience_weight", 0.3)
        self.projects_weight = matching_config.get("projects_weight", 0.2)
        self.min_skill_match = matching_config.get("min_skill_match", 60)
    
    def match(self, job: Job) -> MatchResult:
        """
        Calculate match score between a job and user profile.
        
        Args:
            job: The job to evaluate
            
        Returns:
            MatchResult with detailed scoring
        """
        # Extract technologies from job description
        job_techs = self.tech_extractor.extract_all(job.description)
        job.skills_found = job_techs
        
        # Calculate individual scores
        skills_score = self._calculate_skills_score(job_techs)
        experience_score = self._calculate_experience_score(job)
        title_score = self._calculate_title_score(job.title)
        project_score = self._calculate_project_relevance(job_techs)
        
        # Calculate weighted overall score
        overall_score = (
            skills_score * self.skills_weight +
            experience_score * self.experience_weight +
            title_score * 0.3 +  # Title match has fixed 0.3 weight
            project_score * self.projects_weight
        )
        
        # Normalize to 0-100
        overall_score = min(100, max(0, overall_score))
        
        # Find matched and missing skills
        user_skills = self.profile.get_skills_set()
        matched_skills, missing_skills = self.tech_extractor.find_matching_skills(
            job_techs, user_skills
        )
        
        # Create match score
        score = MatchScore(
            overall_score=overall_score,
            skills_match=skills_score,
            experience_match=experience_score,
            title_match=title_score,
            project_relevance=project_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(job, score, matched_skills, missing_skills)
        
        # Add notes
        notes = []
        if job.remote:
            notes.append("✓ Remote position")
        if len(matched_skills) > 5:
            notes.append(f"✓ Strong tech stack match ({len(matched_skills)} skills)")
        if missing_skills:
            notes.append(f"! Missing {len(missing_skills)} skills")
        
        return MatchResult(
            job=job,
            score=score,
            recommendation=recommendation,
            notes=notes,
        )
    
    def match_batch(self, jobs: List[Job]) -> List[MatchResult]:
        """
        Match multiple jobs against profile.
        
        Args:
            jobs: List of jobs to evaluate
            
        Returns:
            List of MatchResults sorted by score (descending)
        """
        results = [self.match(job) for job in jobs]
        results.sort(key=lambda r: r.score.overall_score, reverse=True)
        return results
    
    def _calculate_skills_score(self, job_techs: List[str]) -> float:
        """Calculate skills match score (0-100)."""
        if not job_techs:
            return 50  # Neutral score if no tech found
        
        user_skills = self.profile.get_skills_set()
        match_percentage = self.tech_extractor.get_skill_match_percentage(
            job_techs, user_skills
        )
        
        return match_percentage
    
    def _calculate_experience_score(self, job: Job) -> float:
        """Calculate experience level match score (0-100)."""
        user_exp = self.profile.experience_years
        
        # Try to extract required experience from description
        exp_patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?',
            r'senior.*?(\d+)\s*years?',
            r'junior.*?(\d+)\s*years?',
            r'mid.*?level.*?(\d+)\s*years?',
        ]
        
        required_exp = None
        for pattern in exp_patterns:
            match = re.search(pattern, job.description, re.IGNORECASE)
            if match:
                required_exp = int(match.group(1))
                break
        
        if required_exp is None:
            # Try to infer from experience level field
            level = (job.experience_level or "").lower()
            if "senior" in level or "lead" in level:
                required_exp = 5
            elif "mid" in level:
                required_exp = 3
            elif "junior" in level or "entry" in level:
                required_exp = 1
            else:
                return 70  # Neutral if can't determine
        
        # Calculate score based on how well user matches
        if user_exp >= required_exp:
            return 100
        else:
            # Partial credit if close
            gap = required_exp - user_exp
            if gap <= 1:
                return 80
            elif gap <= 2:
                return 60
            else:
                return 40
    
    def _calculate_title_score(self, job_title: str) -> float:
        """Calculate job title match score (0-100)."""
        preferred_titles = self.profile.get_preferred_titles()
        job_title_lower = job_title.lower()
        
        # Check for exact matches
        for title in preferred_titles:
            if title.lower() in job_title_lower:
                return 100
        
        # Check for partial matches
        title_keywords = ["engineer", "developer", "architect", "lead", "senior"]
        for keyword in title_keywords:
            if keyword in job_title_lower:
                return 70
        
        return 40  # Low score for unrelated titles
    
    def _calculate_project_relevance(self, job_techs: List[str]) -> float:
        """Calculate project relevance score (0-100)."""
        if not self.profile.projects:
            return 50  # Neutral if no projects
        
        job_techs_lower = set(t.lower() for t in job_techs)
        
        # Check how many projects have overlapping technologies
        matching_projects = 0
        for project in self.profile.projects:
            project_techs = project.get_technologies_set()
            if job_techs_lower.intersection(project_techs):
                matching_projects += 1
        
        if matching_projects == 0:
            return 30
        elif matching_projects == 1:
            return 60
        elif matching_projects == 2:
            return 80
        else:
            return 100
    
    def _generate_recommendation(
        self, 
        job: Job, 
        score: MatchScore,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> str:
        """Generate a recommendation string."""
        if score.overall_score >= 80:
            base = "Excellent match! Highly recommended to apply."
        elif score.overall_score >= 60:
            base = "Good match. Consider applying."
        elif score.overall_score >= 40:
            base = "Moderate match. Review requirements carefully."
        else:
            base = "Low match. May not be the best fit."
        
        # Add specific advice
        if missing_skills and len(missing_skills) <= 3:
            base += f" Consider highlighting experience with {', '.join(missing_skills[:2])}."
        
        if score.experience_match < 50:
            base += " Emphasize relevant projects and transferable skills."
        
        return base
    
    def filter_by_threshold(
        self, 
        results: List[MatchResult], 
        threshold: float = 60.0
    ) -> List[MatchResult]:
        """
        Filter match results by minimum score threshold.
        
        Args:
            results: List of match results
            threshold: Minimum score to include (0-100)
            
        Returns:
            Filtered list of results
        """
        return [r for r in results if r.score.overall_score >= threshold]
