"""Job matcher that compares jobs against user profile."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..models.job import Job
from ..models.match_result import MatchResult, MatchScore
from ..models.profile import UserProfile
from .tech_extractor import TechStackExtractor

# Fixed weights (normalized — sum to 1.0)
WEIGHT_SKILLS = 0.45
WEIGHT_TITLE = 0.20
WEIGHT_EXPERIENCE = 0.20
WEIGHT_PROJECT = 0.15

# If the job shares no extracted tech with the profile, cap overall score.
MAX_SCORE_WITHOUT_SKILL_OVERLAP = 55.0


class JobMatcher:
    """Matches jobs against user profile and calculates match scores."""

    def __init__(self, profile: UserProfile, config: Optional[Dict] = None):
        """
        Initialize the job matcher.

        Args:
            profile: User's profile with skills and experience
            config: Optional configuration (priority keywords, legacy keys)
        """
        self.profile = profile
        self.config = config or {}
        self.tech_extractor = TechStackExtractor()

    def match(self, job: Job) -> MatchResult:
        """
        Calculate match score between a job and user profile.

        Uses normalized weights:
        skills 45%, title 20%, experience 20%, project relevance 15%.
        If there is zero overlap between profile skills and job tech hits,
        the overall score is capped at 55.
        """
        job_techs = self.tech_extractor.extract_all(job.description)
        job.skills_found = job_techs

        user_skills = self.profile.get_skills_set()
        matched_skills, missing_skills = self.tech_extractor.find_matching_skills(
            job_techs,
            user_skills,
        )

        skills_score = self._calculate_skills_score(job_techs)
        experience_score = self._calculate_experience_score(job)
        title_score = self._calculate_title_score(job.title)
        project_score = self._calculate_project_relevance(job_techs)

        overall = (
            skills_score * WEIGHT_SKILLS
            + title_score * WEIGHT_TITLE
            + experience_score * WEIGHT_EXPERIENCE
            + project_score * WEIGHT_PROJECT
        )
        overall = min(100.0, max(0.0, overall))

        if len(matched_skills) == 0:
            overall = min(overall, MAX_SCORE_WITHOUT_SKILL_OVERLAP)

        matched_keywords = self._priority_keywords_found(job)

        breakdown = {
            "skills_score": round(skills_score / 100.0, 4),
            "title_score": round(title_score / 100.0, 4),
            "experience_score": round(experience_score / 100.0, 4),
            "project_score": round(project_score / 100.0, 4),
            "weights": {
                "skills": WEIGHT_SKILLS,
                "title": WEIGHT_TITLE,
                "experience": WEIGHT_EXPERIENCE,
                "project": WEIGHT_PROJECT,
            },
            "matched_skill_count": len(matched_skills),
            "no_skill_overlap_cap": len(matched_skills) == 0,
            "final_score": round(overall, 2),
        }

        score = MatchScore(
            overall_score=overall,
            skills_match=skills_score,
            experience_match=experience_score,
            title_match=title_score,
            project_relevance=project_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            matched_keywords=matched_keywords,
            score_breakdown=breakdown,
        )

        recommendation = self._generate_recommendation(
            job,
            score,
            matched_skills,
            missing_skills,
        )

        notes = []
        if job.remote:
            notes.append("✓ Remote position")
        if len(matched_skills) > 5:
            notes.append(
                f"✓ Strong tech stack match ({len(matched_skills)} skills)",
            )
        if missing_skills:
            notes.append(f"! Missing {len(missing_skills)} skills")

        return MatchResult(
            job=job,
            score=score,
            recommendation=recommendation,
            notes=notes,
        )

    def match_batch(self, jobs: List[Job]) -> List[MatchResult]:
        """Match multiple jobs; results sorted by score descending."""
        results = [self.match(job) for job in jobs]
        results.sort(key=lambda r: r.score.overall_score, reverse=True)
        return results

    def _priority_keywords_found(self, job: Job) -> List[str]:
        """Search-config priority keywords present in title or description."""
        kws = self.config.get("search", {}).get("priority_keywords", [])
        if not kws:
            return []
        blob = f"{job.title} {job.description}".lower()
        found: List[str] = []
        for kw in kws:
            if isinstance(kw, str) and kw.lower() in blob:
                found.append(kw)
        return found

    def _calculate_skills_score(self, job_techs: List[str]) -> float:
        """Skills match score (0-100)."""
        if not job_techs:
            return 0.0

        user_skills = self.profile.get_skills_set()
        return self.tech_extractor.get_skill_match_percentage(
            job_techs,
            user_skills,
        )

    def _calculate_experience_score(self, job: Job) -> float:
        """Experience level match score (0-100)."""
        user_exp = self.profile.experience_years

        exp_patterns = [
            r"(\d+)\+?\s*years?",
            r"(\d+)\+?\s*yrs?",
            r"senior.*?(\d+)\s*years?",
            r"junior.*?(\d+)\s*years?",
            r"mid.*?level.*?(\d+)\s*years?",
        ]

        required_exp = None
        for pattern in exp_patterns:
            match = re.search(pattern, job.description, re.IGNORECASE)
            if match:
                required_exp = int(match.group(1))
                break

        if required_exp is None:
            level = (job.experience_level or "").lower()
            if "senior" in level or "lead" in level:
                required_exp = 5
            elif "mid" in level:
                required_exp = 3
            elif "junior" in level or "entry" in level:
                required_exp = 1
            else:
                return 70.0

        if user_exp >= required_exp:
            return 100.0
        gap = required_exp - user_exp
        if gap <= 1:
            return 80.0
        if gap <= 2:
            return 60.0
        return 40.0

    def _calculate_title_score(self, job_title: str) -> float:
        """Job title match score (0-100)."""
        preferred_titles = self.profile.get_preferred_titles()
        job_title_lower = job_title.lower()

        for title in preferred_titles:
            if title.lower() in job_title_lower:
                return 100.0

        title_keywords = [
            "engineer",
            "developer",
            "architect",
            "lead",
            "senior",
        ]
        for keyword in title_keywords:
            if keyword in job_title_lower:
                return 70.0

        return 40.0

    def _calculate_project_relevance(self, job_techs: List[str]) -> float:
        """Project relevance score (0-100)."""
        if not self.profile.projects:
            return 50.0

        job_techs_lower = {t.lower() for t in job_techs}

        matching_projects = 0
        for project in self.profile.projects:
            project_techs = project.get_technologies_set()
            if job_techs_lower.intersection(project_techs):
                matching_projects += 1

        if matching_projects == 0:
            return 30.0
        if matching_projects == 1:
            return 60.0
        if matching_projects == 2:
            return 80.0
        return 100.0

    def _generate_recommendation(
        self,
        job: Job,
        score: MatchScore,
        matched_skills: List[str],
        missing_skills: List[str],
    ) -> str:
        """Generate a recommendation string."""
        band = score.get_quality_band()
        if band == "Excellent":
            base = "Excellent match! Highly recommended to apply."
        elif band == "Strong":
            base = "Strong match. Worth prioritizing."
        elif band == "Maybe":
            base = "Possible fit. Review requirements and gaps carefully."
        else:
            base = "Weak match or missing core skill overlap."

        if missing_skills and len(missing_skills) <= 3:
            base += (
                f" Consider highlighting experience with "
                f"{', '.join(missing_skills[:2])}."
            )

        if score.experience_match < 50:
            base += " Emphasize relevant projects and transferable skills."

        return base

    def filter_by_threshold(
        self,
        results: List[MatchResult],
        threshold: float = 60.0,
    ) -> List[MatchResult]:
        """Filter match results by minimum score threshold."""
        return [r for r in results if r.score.overall_score >= threshold]
