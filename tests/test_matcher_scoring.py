"""Tests for normalized job matching scores."""

from unittest.mock import patch

import pytest

from src.matcher.matcher import JobMatcher, MAX_SCORE_WITHOUT_SKILL_OVERLAP
from src.models.job import Job, JobSource
from src.models.profile import Skill, UserProfile


def _profile(**kwargs) -> UserProfile:
    defaults = dict(
        name="Test",
        email="t@example.com",
        description="",
        experience_years=5,
        skills=[Skill(name="Python")],
        job_titles=["Software Engineer"],
        projects=[],
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def _job(**kwargs) -> Job:
    d = dict(
        title="Software Engineer",
        company="Co",
        location="Remote",
        description="Job description text",
        source=JobSource.INDEED,
        url="https://example.com/j/1",
    )
    d.update(kwargs)
    return Job(**d)


def test_no_skill_overlap_caps_score():
    profile = _profile()
    job = _job()
    matcher = JobMatcher(profile, {})

    with patch.object(
        matcher.tech_extractor,
        "extract_all",
        return_value=["java", "kotlin"],
    ):
        with patch.object(matcher, "_calculate_title_score", return_value=100.0):
            with patch.object(matcher, "_calculate_experience_score", return_value=100.0):
                with patch.object(
                    matcher,
                    "_calculate_project_relevance",
                    return_value=100.0,
                ):
                    r = matcher.match(job)

    assert len(r.score.matched_skills) == 0
    assert r.score.overall_score <= MAX_SCORE_WITHOUT_SKILL_OVERLAP
    assert r.score.get_quality_band() in ("Maybe", "Weak")


def test_excellent_requires_matched_skill():
    profile = _profile()
    job = _job()
    matcher = JobMatcher(profile, {})

    with patch.object(
        matcher.tech_extractor,
        "extract_all",
        return_value=["python"],
    ):
        with patch.object(matcher, "_calculate_skills_score", return_value=100.0):
            with patch.object(matcher, "_calculate_title_score", return_value=100.0):
                with patch.object(
                    matcher,
                    "_calculate_experience_score",
                    return_value=100.0,
                ):
                    with patch.object(
                        matcher,
                        "_calculate_project_relevance",
                        return_value=100.0,
                    ):
                        r = matcher.match(job)

    assert len(r.score.matched_skills) > 0
    assert r.score.overall_score >= 85
    assert r.score.get_quality_band() == "Excellent"


def test_weights_sum_normalized():
    """Subscores at 100 produce overall 100 when skills overlap exists."""
    profile = _profile()
    job = _job()
    matcher = JobMatcher(profile, {})

    with patch.object(
        matcher.tech_extractor,
        "extract_all",
        return_value=["python"],
    ):
        with patch.object(matcher, "_calculate_skills_score", return_value=100.0):
            with patch.object(matcher, "_calculate_title_score", return_value=100.0):
                with patch.object(
                    matcher,
                    "_calculate_experience_score",
                    return_value=100.0,
                ):
                    with patch.object(
                        matcher,
                        "_calculate_project_relevance",
                        return_value=100.0,
                    ):
                        r = matcher.match(job)

    assert abs(r.score.overall_score - 100.0) < 0.01
    assert r.score.score_breakdown["final_score"] == pytest.approx(100.0, rel=0.01)
