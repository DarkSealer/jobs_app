"""
Orchestration for Job Radar: YAML merge, search runs, and persistence.

Streamlit pages should call functions here instead of touching scrapers
or raw SQL directly.
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import yaml

from src.gui import database as db
from src.matcher import JobMatcher
from src.models.job import Job
from src.models.match_result import MatchResult
from src.models.profile import Project, Skill, UserProfile
from src.scraper import ScraperManager
from src.scraper.registry import (
    SOURCE_REGISTER_ORDER,
    register_default_scrapers,
    source_key_allowed,
)

log = logging.getLogger(__name__)

SETTINGS_CONFIG_PATH = "config_yaml_path"

SCRAPER_CLASS_TO_SOURCE: Dict[str, str] = {
    "IndeedScraper": "indeed",
    "LinkedInScraper": "linkedin",
    "GlassdoorScraper": "glassdoor",
    "RemotiveScraper": "remotive",
    "WeWorkRemotelyScraper": "weworkremotely",
    "RemoteOkScraper": "remoteok",
    "WellfoundScraper": "wellfound",
    "BuiltInScraper": "builtin",
    "DiceScraper": "dice",
    "GreenhouseScraper": "greenhouse",
    "LeverScraper": "lever",
    "UpworkScraper": "upwork",
}

# (name, source_type, notes) — default enabled True until YAML seed applies
CANONICAL_SOURCES: Tuple[Tuple[str, str, str], ...] = (
    ("indeed", "Website", "Automated listing search."),
    ("linkedin", "Browser Manual", "Not run from Job Radar search."),
    ("glassdoor", "Browser Manual", "Not run from Job Radar search."),
    ("remotive", "Public API", "Public listings feed."),
    ("weworkremotely", "Website", "Public job feed."),
    ("remoteok", "Website", "Public feed / API."),
    ("wellfound", "Website", "HTML listings."),
    ("builtin", "Website", "Built In regional boards."),
    ("dice", "Website", "Dice search."),
    ("greenhouse", "Career Board API", "Greenhouse JSON boards."),
    ("lever", "Career Board API", "Lever JSON boards."),
    ("upwork", "Browser Manual", "Not run from Job Radar search."),
)


def get_config_path(db_path: Optional[Path] = None) -> Path:
    """Resolved path to job search YAML (CLI-compatible)."""
    raw = db.get_setting(SETTINGS_CONFIG_PATH, "config.yaml", db_path)
    p = Path(raw)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def set_config_path(path: str, db_path: Optional[Path] = None) -> None:
    db.set_setting(SETTINGS_CONFIG_PATH, path, db_path)


def load_yaml_config(config_path: Optional[Path] = None) -> dict:
    """Load config.yaml (or missing path returns {})."""
    path = config_path or get_config_path()
    if not path.exists():
        log.warning("Config file not found: %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("Could not load YAML %s: %s", path, e)
        return {}


def seed_job_sources_if_empty(
    yaml_config: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Insert default job_sources once."""
    db.init_db(db_path)
    if db.list_sources(db_path):
        return
    y = yaml_config or load_yaml_config(db_path)
    boards = y.get("job_boards", {})
    rows: List[Tuple[str, str, bool, str, str]] = []
    for name, source_type, note in CANONICAL_SOURCES:
        enabled = bool(boards.get(name, {}).get("enabled", True))
        rows.append((name, source_type, enabled, "Idle", note))
    db.reinitialize_sources_metadata(rows, db_path)


def init_gui_db(db_path: Optional[Path] = None) -> None:
    db.init_db(db_path)
    seed_job_sources_if_empty(load_yaml_config(get_config_path(db_path)), db_path)


def db_enabled_source_names(db_path: Optional[Path] = None) -> Set[str]:
    return {
        r["name"]
        for r in db.list_sources(db_path)
        if r["enabled"]
    }


def build_user_profile(
    row: db.ProfileRow,
    yaml_config: dict,
) -> UserProfile:
    """Build UserProfile from SQLite row, merging projects from YAML if empty."""
    skills = [Skill(name=s) for s in row.skills if isinstance(s, str) and s.strip()]
    titles = [t for t in row.target_titles if isinstance(t, str) and t.strip()]

    projects_data: List[dict] = list(row.projects or [])
    if not projects_data:
        raw = yaml_config.get("profile", {}).get("projects", [])
        projects_data = [p for p in raw if isinstance(p, dict)]

    projects: List[Project] = []
    for p in projects_data:
        try:
            projects.append(
                Project(
                    name=str(p.get("name", "Project")),
                    description=str(p.get("description", "")),
                    technologies=list(p.get("technologies", [])),
                    url=p.get("url"),
                ),
            )
        except (TypeError, KeyError) as e:
            log.debug("Skip bad project row: %s", e)

    return UserProfile(
        name=row.name or "Unknown",
        email=row.email or "",
        description=row.summary or "",
        experience_years=int(row.years_experience or 0),
        skills=skills,
        job_titles=titles,
        projects=projects,
    )


def matcher_config_for_profile(
    yaml_config: dict,
    profile_row: db.ProfileRow,
) -> dict:
    """YAML config overlay so JobMatcher sees search priority keywords."""
    cfg = copy.deepcopy(yaml_config) if yaml_config else {}
    search = cfg.setdefault("search", {})
    pk = set(search.get("priority_keywords", []))
    for s in profile_row.skills:
        if isinstance(s, str) and s.strip():
            pk.add(s.strip())
    search["priority_keywords"] = list(pk)
    return cfg


def _job_excluded(job: Job, keywords: Sequence[str]) -> bool:
    if not keywords:
        return False
    blob = f"{job.title} {job.description}".lower()
    return any(k.strip().lower() in blob for k in keywords if k.strip())


def resolve_enabled_sources_for_run(
    yaml_config: dict,
    preset_enabled: Sequence[str],
    db_path: Optional[Path] = None,
) -> Set[str]:
    """
    Intersection of YAML-enabled boards, DB-enabled toggles, preset list.

    Preset empty means 'all DB-enabled non-manual keys'.
    """
    db_on = db_enabled_source_names(db_path)
    preset_set = {x.strip().lower() for x in preset_enabled if x.strip()}
    if not preset_set:
        candidates = set(db_on)
    else:
        candidates = preset_set & db_on

    out: Set[str] = set()
    for key in SOURCE_REGISTER_ORDER:
        if key not in candidates:
            continue
        if source_key_allowed(
            key,
            yaml_config,
            enabled_sources=None,
            db_enabled_sources=db_on,
            skip_manual=True,
        ):
            out.add(key)
    return out


@dataclass
class SearchRunReport:
    """Summary returned after ``run_search``."""

    run_id: int
    total_found: int
    total_matched: int
    duration_seconds: float
    sources_registered: List[str] = field(default_factory=list)
    source_errors: Dict[str, str] = field(default_factory=dict)
    status: str = "completed"
    error_message: Optional[str] = None


def run_search(
    role_keywords: Sequence[str],
    locations: Sequence[str],
    remote_only: bool,
    minimum_score: float,
    result_limit: int,
    preset_enabled_sources: Sequence[str],
    excluded_keywords: Sequence[str],
    db_path: Optional[Path] = None,
) -> SearchRunReport:
    """
    Execute a multi-board search, match, persist jobs and match_results.

    Manual sources (LinkedIn, Glassdoor, Upwork) are never scraped here.
    """
    init_gui_db(db_path)
    yaml_config = load_yaml_config(get_config_path(db_path))
    profile_row = db.get_or_create_default_profile(db_path)
    profile = build_user_profile(profile_row, yaml_config)
    matcher_cfg = matcher_config_for_profile(yaml_config, profile_row)

    excl = list(
        dict.fromkeys(
            list(profile_row.excluded_keywords)
            + list(excluded_keywords),
        ),
    )

    search_locations = list(locations) if locations else ["Remote"]
    search_queries = [q for q in role_keywords if q.strip()]
    if not search_queries:
        search_queries = profile.get_preferred_titles()

    include_remote = remote_only or yaml_config.get("search", {}).get(
        "include_remote",
        True,
    )
    if remote_only:
        search_locations = ["Remote"]

    enabled_keys = resolve_enabled_sources_for_run(
        yaml_config,
        preset_enabled_sources,
        db_path,
    )

    run_id = db.save_search_run_start(db_path)
    t0 = time.perf_counter()
    source_errors: Dict[str, str] = {}
    sources_registered = [k for k in SOURCE_REGISTER_ORDER if k in enabled_keys]

    try:
        manager = ScraperManager(yaml_config)
        register_default_scrapers(
            manager,
            yaml_config,
            enabled_sources=enabled_keys,
            db_enabled_sources=db_enabled_source_names(db_path),
            skip_manual=True,
            echo_registered=None,
        )

        all_jobs: List[Job] = []
        n_loc = max(1, len(search_locations))
        n_q = max(1, len(search_queries))
        limit_per_board = max(1, result_limit // n_loc // n_q)

        for loc in search_locations:
            for job_query in search_queries:
                loc_param = loc if loc.lower() != "remote" else None
                remote_flag = include_remote and loc.lower() == "remote"
                _jobs, errs = manager.search_all_reporting(
                    query=job_query,
                    location=loc_param,
                    remote=remote_flag,
                    limit_per_board=limit_per_board,
                    verbose=False,
                )
                for class_name, msg in errs:
                    key = SCRAPER_CLASS_TO_SOURCE.get(class_name)
                    if key:
                        source_errors[key] = msg
                        log.warning("Scraper error %s: %s", class_name, msg)
                all_jobs.extend(_jobs)

        manager.close_all()
        all_jobs = manager.remove_duplicates(all_jobs)
        all_jobs = [j for j in all_jobs if not _job_excluded(j, excl)]

        matcher = JobMatcher(profile, matcher_cfg)
        match_results = matcher.match_batch(all_jobs)

        total_matched = sum(
            1 for r in match_results if r.score.overall_score >= minimum_score
        )

        for result in match_results:
            _persist_match_result(result, run_id, db_path)

        for key in sources_registered:
            if key in source_errors:
                db.update_source_health(
                    key,
                    "Error",
                    source_errors[key],
                    db_path=db_path,
                )
            else:
                db.update_source_health(key, "OK", None, db_path=db_path)

        duration = time.perf_counter() - t0
        db.save_search_run_finish(
            run_id,
            "completed",
            len(all_jobs),
            total_matched,
            None,
            db_path=db_path,
        )

        return SearchRunReport(
            run_id=run_id,
            total_found=len(all_jobs),
            total_matched=total_matched,
            duration_seconds=duration,
            sources_registered=sources_registered,
            source_errors=source_errors,
            status="completed",
        )

    except Exception as e:
        log.exception("Search run failed")
        duration = time.perf_counter() - t0
        db.save_search_run_finish(
            run_id,
            "failed",
            0,
            0,
            str(e),
            db_path=db_path,
        )
        return SearchRunReport(
            run_id=run_id,
            total_found=0,
            total_matched=0,
            duration_seconds=duration,
            sources_registered=sources_registered,
            source_errors=source_errors,
            status="failed",
            error_message=str(e),
        )


def _persist_match_result(
    result: MatchResult,
    search_run_id: int,
    db_path: Optional[Path],
) -> None:
    job = result.job
    ext = db.job_external_id(job.url or f"{job.source}:{job.title}:{job.company}")
    raw = job.to_dict()
    posted = None
    if job.posted_date:
        posted = job.posted_date.isoformat()

    jid = db.upsert_job(
        external_id=ext,
        title=job.title,
        company=job.company,
        location=job.location or "",
        source=job.source.value if hasattr(job.source, "value") else str(job.source),
        url=job.url or "",
        salary=job.salary_range,
        description=job.description or "",
        date_posted=posted,
        raw_data=raw,
        db_path=db_path,
    )

    db.save_match_result(
        job_id=jid,
        search_run_id=search_run_id,
        score=result.score.overall_score,
        grade=result.score.get_grade(),
        quality_band=result.score.get_quality_band(),
        matched_skills=result.score.matched_skills,
        missing_skills=result.score.missing_skills,
        matched_keywords=result.score.matched_keywords,
        score_breakdown=result.score.score_breakdown,
        db_path=db_path,
    )


def compute_profile_strength(row: db.ProfileRow) -> Tuple[int, List[str]]:
    """
    Simple completeness score (0–100) and improvement hints.
    """
    score = 0
    hints: List[str] = []
    if (row.summary or "").strip():
        score += 20
    else:
        hints.append("Add a professional summary.")
    skills = [s for s in row.skills if isinstance(s, str) and s.strip()]
    if len(skills) >= 5:
        score += 20
    else:
        hints.append("Add at least five distinct skills.")
    titles = [t for t in row.target_titles if isinstance(t, str) and t.strip()]
    if len(titles) >= 2:
        score += 20
    else:
        hints.append("Add at least two target job titles.")
    locs = [x for x in row.locations if isinstance(x, str) and x.strip()]
    if len(locs) >= 1:
        score += 15
    else:
        hints.append("Add at least one preferred location (or Remote).")
    if row.years_experience and row.years_experience > 0:
        score += 10
    else:
        hints.append("Set years of experience.")
    excl = [x for x in row.excluded_keywords if isinstance(x, str) and x.strip()]
    if excl:
        score += 10
    else:
        hints.append("Add excluded keywords to filter noise.")
    if row.minimum_salary is not None and row.minimum_salary > 0:
        score += 5
    else:
        hints.append("Optionally set a minimum salary expectation.")
    return min(100, score), hints


def build_why_and_risks(
    result_summary: Dict[str, Any],
    min_score: float,
) -> Tuple[List[str], List[str]]:
    """
    Heuristic bullets from persisted match + job fields (no LLM).

    ``result_summary`` should include keys like score, matched_skills,
    missing_skills, title_match, remote, salary, location, score_breakdown.
    """
    why: List[str] = []
    risks: List[str] = []

    score = float(result_summary.get("score") or 0)
    matched = result_summary.get("matched_skills") or []
    if isinstance(matched, str):
        import json

        matched = json.loads(matched) if matched.startswith("[") else matched.split(",")

    title_m = float(result_summary.get("title_match") or 0)
    if title_m >= 80:
        why.append("Strong title alignment with your targets.")

    if isinstance(matched, list) and len(matched) >= 3:
        why.append("Several profile skills appear in the posting.")
    elif isinstance(matched, list) and len(matched) >= 1:
        why.append("Some profile skills appear in the posting.")

    if result_summary.get("remote"):
        why.append("Remote-friendly role.")

    bd = result_summary.get("score_breakdown") or {}
    if isinstance(bd, str):
        import json

        try:
            bd = json.loads(bd)
        except json.JSONDecodeError:
            bd = {}
    if bd.get("matched_skill_count", 0) > 0 and float(bd.get("project_score", 0) or 0) >= 0.5:
        why.append("Project stack overlap suggests relevant experience.")

    missing = result_summary.get("missing_skills") or []
    if isinstance(missing, str):
        import json

        try:
            missing = json.loads(missing)
        except json.JSONDecodeError:
            missing = []
    if isinstance(missing, list) and len(missing) >= 5:
        risks.append("Many skills in the posting are not in your profile.")
    elif isinstance(missing, list) and len(missing) >= 1 and len(matched or []) == 0:
        risks.append("Missing overlap between profile skills and posting tech.")

    if not (result_summary.get("salary") or "").strip():
        risks.append("Salary not stated in listing.")

    if score < min_score:
        risks.append("Score is below your current minimum threshold.")

    if not result_summary.get("remote") and "remote" not in str(
        result_summary.get("location", ""),
    ).lower():
        risks.append("Location may not match a remote-first search.")

    return why, risks


def reseed_sources_metadata(db_path: Optional[Path] = None) -> None:
    """Settings: refresh source types / notes from defaults + YAML."""
    y = load_yaml_config(get_config_path(db_path))
    boards = y.get("job_boards", {})
    rows: List[Tuple[str, str, bool, str, str]] = []
    for name, source_type, note in CANONICAL_SOURCES:
        en = bool(boards.get(name, {}).get("enabled", True))
        rows.append((name, source_type, en, "Idle", note))
    db.reinitialize_sources_metadata(rows, db_path)
