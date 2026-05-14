"""
SQLite persistence for Job Radar.

All SQL lives here; Streamlit pages should call these helpers, not raw SQL.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Iterable, List, Optional, Sequence, Tuple

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "jobs.db"

APPLICATION_STATUSES: Tuple[str, ...] = (
    "New",
    "Saved",
    "Apply Today",
    "Applied",
    "Interview",
    "Rejected",
    "Ghosted",
    "Not Interested",
)

CURRENT_SCHEMA_VERSION = 1


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: Optional[str], default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return default


@contextmanager
def get_connection(
    db_path: Optional[Path] = None,
) -> Generator[sqlite3.Connection, None, None]:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA user_version")
    version = int(cur.fetchone()[0])
    if version < 1:
        conn.executescript(_SCHEMA_V1)
        conn.execute(f"PRAGMA user_version = {int(CURRENT_SCHEMA_VERSION)}")


_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    years_experience INTEGER NOT NULL DEFAULT 0,
    skills TEXT NOT NULL DEFAULT '[]',
    target_titles TEXT NOT NULL DEFAULT '[]',
    locations TEXT NOT NULL DEFAULT '[]',
    remote_only INTEGER NOT NULL DEFAULT 0,
    minimum_salary INTEGER,
    excluded_keywords TEXT NOT NULL DEFAULT '[]',
    projects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL DEFAULT 'Website',
    enabled INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'Idle',
    last_checked_at TEXT,
    last_error TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role_keywords TEXT NOT NULL DEFAULT '[]',
    locations TEXT NOT NULL DEFAULT '[]',
    remote_only INTEGER NOT NULL DEFAULT 0,
    job_type TEXT,
    minimum_score REAL NOT NULL DEFAULT 60,
    enabled_sources TEXT NOT NULL DEFAULT '[]',
    excluded_keywords TEXT NOT NULL DEFAULT '[]',
    result_limit INTEGER NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    total_found INTEGER NOT NULL DEFAULT 0,
    total_matched INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    salary TEXT,
    description TEXT NOT NULL DEFAULT '',
    date_posted TEXT,
    discovered_at TEXT NOT NULL,
    raw_data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    search_run_id INTEGER NOT NULL REFERENCES search_runs(id),
    score REAL NOT NULL,
    grade TEXT NOT NULL,
    quality_band TEXT,
    matched_skills TEXT NOT NULL DEFAULT '[]',
    missing_skills TEXT NOT NULL DEFAULT '[]',
    matched_keywords TEXT NOT NULL DEFAULT '[]',
    score_breakdown TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(job_id, search_run_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id),
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT NOT NULL DEFAULT '',
    applied_at TEXT,
    next_action_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
CREATE INDEX IF NOT EXISTS idx_jobs_external ON jobs(external_id);
CREATE INDEX IF NOT EXISTS idx_match_job ON match_results(job_id);
CREATE INDEX IF NOT EXISTS idx_match_run ON match_results(search_run_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
"""


def init_db(db_path: Optional[Path] = None) -> None:
    """Create tables and apply migrations."""
    with get_connection(db_path) as conn:
        _migrate(conn)


def get_setting(key: str, default: str = "", db_path: Optional[Path] = None) -> str:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str, db_path: Optional[Path] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


@dataclass
class ProfileRow:
    id: int
    name: str
    email: str
    summary: str
    years_experience: int
    skills: List[str]
    target_titles: List[str]
    locations: List[str]
    remote_only: bool
    minimum_salary: Optional[int]
    excluded_keywords: List[str]
    projects: List[dict]


def _row_to_profile(row: sqlite3.Row) -> ProfileRow:
    return ProfileRow(
        id=row["id"],
        name=row["name"] or "",
        email=row["email"] or "",
        summary=row["summary"] or "",
        years_experience=int(row["years_experience"] or 0),
        skills=list(_json_loads(row["skills"], [])),
        target_titles=list(_json_loads(row["target_titles"], [])),
        locations=list(_json_loads(row["locations"], [])),
        remote_only=bool(row["remote_only"]),
        minimum_salary=row["minimum_salary"],
        excluded_keywords=list(_json_loads(row["excluded_keywords"], [])),
        projects=list(_json_loads(row["projects_json"], [])),
    )


def get_or_create_default_profile(db_path: Optional[Path] = None) -> ProfileRow:
    """Return the primary profile (single-user v1: first row)."""
    init_db(db_path)
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM profiles ORDER BY id LIMIT 1").fetchone()
        if row:
            return _row_to_profile(row)
        conn.execute(
            """
            INSERT INTO profiles (
                name, email, summary, years_experience,
                skills, target_titles, locations, remote_only,
                minimum_salary, excluded_keywords, projects_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "",
                "",
                "",
                0,
                _json_dumps([]),
                _json_dumps([]),
                _json_dumps([]),
                0,
                None,
                _json_dumps([]),
                _json_dumps([]),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM profiles ORDER BY id DESC LIMIT 1").fetchone()
        return _row_to_profile(row)


def save_profile(
    profile_id: int,
    name: str,
    email: str,
    summary: str,
    years_experience: int,
    skills: Sequence[str],
    target_titles: Sequence[str],
    locations: Sequence[str],
    remote_only: bool,
    minimum_salary: Optional[int],
    excluded_keywords: Sequence[str],
    projects: Optional[Sequence[dict]] = None,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    projects_list = list(projects) if projects is not None else []
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE profiles SET
                name = ?, email = ?, summary = ?, years_experience = ?,
                skills = ?, target_titles = ?, locations = ?, remote_only = ?,
                minimum_salary = ?, excluded_keywords = ?, projects_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                email,
                summary,
                years_experience,
                _json_dumps(list(skills)),
                _json_dumps(list(target_titles)),
                _json_dumps(list(locations)),
                1 if remote_only else 0,
                minimum_salary,
                _json_dumps(list(excluded_keywords)),
                _json_dumps(projects_list),
                now,
                profile_id,
            ),
        )


def list_sources(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        return list(
            conn.execute(
                "SELECT * FROM job_sources ORDER BY name COLLATE NOCASE",
            ).fetchall(),
        )


def update_source_enabled(
    source_name: str,
    enabled: bool,
    db_path: Optional[Path] = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE job_sources SET enabled = ? WHERE name = ?",
            (1 if enabled else 0, source_name),
        )


def update_source_health(
    source_name: str,
    status: str,
    last_error: Optional[str],
    last_checked_at: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    checked = last_checked_at or datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE job_sources SET
                status = ?, last_error = ?, last_checked_at = ?
            WHERE name = ?
            """,
            (status, last_error, checked, source_name),
        )


def upsert_job_sources(
    rows: Iterable[Tuple[str, str, bool, str, str]],
    db_path: Optional[Path] = None,
) -> None:
    """
    rows: (name, source_type, enabled, status, notes)
    Insert or replace metadata; preserves enabled if row exists (merge).
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        for name, source_type, enabled, status, notes in rows:
            existing = conn.execute(
                "SELECT enabled FROM job_sources WHERE name = ?",
                (name,),
            ).fetchone()
            en = int(enabled) if existing is None else existing["enabled"]
            conn.execute(
                """
                INSERT INTO job_sources
                    (name, source_type, enabled, status, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    source_type = excluded.source_type,
                    notes = COALESCE(excluded.notes, job_sources.notes)
                """,
                (name, source_type, en, status, notes),
            )


def reinitialize_sources_metadata(
    rows: Iterable[Tuple[str, str, bool, str, str]],
    db_path: Optional[Path] = None,
) -> None:
    """Reseed type/notes/status without deleting historical data."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        for name, source_type, enabled, status, notes in rows:
            conn.execute(
                """
                INSERT INTO job_sources
                    (name, source_type, enabled, status, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    source_type = excluded.source_type,
                    notes = excluded.notes
                """,
                (name, source_type, int(enabled), status, notes),
            )


def create_saved_search(
    name: str,
    role_keywords: Sequence[str],
    locations: Sequence[str],
    remote_only: bool,
    job_type: Optional[str],
    minimum_score: float,
    enabled_sources: Sequence[str],
    excluded_keywords: Sequence[str],
    result_limit: int = 50,
    db_path: Optional[Path] = None,
) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO saved_searches (
                name, role_keywords, locations, remote_only, job_type,
                minimum_score, enabled_sources, excluded_keywords,
                result_limit, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                _json_dumps(list(role_keywords)),
                _json_dumps(list(locations)),
                1 if remote_only else 0,
                job_type or "",
                minimum_score,
                _json_dumps(list(enabled_sources)),
                _json_dumps(list(excluded_keywords)),
                result_limit,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def update_saved_search(
    search_id: int,
    name: str,
    role_keywords: Sequence[str],
    locations: Sequence[str],
    remote_only: bool,
    job_type: Optional[str],
    minimum_score: float,
    enabled_sources: Sequence[str],
    excluded_keywords: Sequence[str],
    result_limit: int = 50,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE saved_searches SET
                name = ?, role_keywords = ?, locations = ?, remote_only = ?,
                job_type = ?, minimum_score = ?, enabled_sources = ?,
                excluded_keywords = ?, result_limit = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                _json_dumps(list(role_keywords)),
                _json_dumps(list(locations)),
                1 if remote_only else 0,
                job_type or "",
                minimum_score,
                _json_dumps(list(enabled_sources)),
                _json_dumps(list(excluded_keywords)),
                result_limit,
                now,
                search_id,
            ),
        )


def list_saved_searches(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        return list(
            conn.execute(
                "SELECT * FROM saved_searches ORDER BY updated_at DESC",
            ).fetchall(),
        )


def get_saved_search(
    search_id: int,
    db_path: Optional[Path] = None,
) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM saved_searches WHERE id = ?",
            (search_id,),
        ).fetchone()


def delete_saved_search(search_id: int, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))


def save_search_run_start(db_path: Optional[Path] = None) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO search_runs
                (started_at, status, total_found, total_matched)
            VALUES (?, 'running', 0, 0)
            """,
            (now,),
        )
        return int(cur.lastrowid)


def save_search_run_finish(
    run_id: int,
    status: str,
    total_found: int,
    total_matched: int,
    error_message: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE search_runs SET
                finished_at = ?, status = ?, total_found = ?,
                total_matched = ?, error_message = ?
            WHERE id = ?
            """,
            (now, status, total_found, total_matched, error_message, run_id),
        )


def get_last_search_run(db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT * FROM search_runs
            WHERE status != 'running'
            ORDER BY id DESC LIMIT 1
            """,
        ).fetchone()


def job_external_id(url: str) -> str:
    import hashlib

    normalized = (url or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def upsert_job(
    external_id: str,
    title: str,
    company: str,
    location: str,
    source: str,
    url: str,
    salary: Optional[str],
    description: str,
    date_posted: Optional[str],
    raw_data: dict,
    db_path: Optional[Path] = None,
) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    raw = _json_dumps(raw_data)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                external_id, title, company, location, source, url,
                salary, description, date_posted, discovered_at, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                source = excluded.source,
                url = excluded.url,
                salary = excluded.salary,
                description = excluded.description,
                date_posted = excluded.date_posted,
                discovered_at = excluded.discovered_at,
                raw_data = excluded.raw_data
            """,
            (
                external_id,
                title,
                company,
                location,
                source,
                url,
                salary,
                description,
                date_posted,
                now,
                raw,
            ),
        )
        row = conn.execute(
            "SELECT id FROM jobs WHERE external_id = ?",
            (external_id,),
        ).fetchone()
        return int(row["id"])


def save_match_result(
    job_id: int,
    search_run_id: int,
    score: float,
    grade: str,
    quality_band: Optional[str],
    matched_skills: Sequence[str],
    missing_skills: Sequence[str],
    matched_keywords: Sequence[str],
    score_breakdown: dict,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO match_results (
                job_id, search_run_id, score, grade, quality_band,
                matched_skills, missing_skills, matched_keywords,
                score_breakdown, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, search_run_id) DO UPDATE SET
                score = excluded.score,
                grade = excluded.grade,
                quality_band = excluded.quality_band,
                matched_skills = excluded.matched_skills,
                missing_skills = excluded.missing_skills,
                matched_keywords = excluded.matched_keywords,
                score_breakdown = excluded.score_breakdown,
                created_at = excluded.created_at
            """,
            (
                job_id,
                search_run_id,
                score,
                grade,
                quality_band or "",
                _json_dumps(list(matched_skills)),
                _json_dumps(list(missing_skills)),
                _json_dumps(list(matched_keywords)),
                _json_dumps(score_breakdown),
                now,
            ),
        )


def ensure_application_row(job_id: int, db_path: Optional[Path] = None) -> int:
    """Return applications.id for this job_id, creating New if missing."""
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM applications WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            """
            INSERT INTO applications
                (job_id, status, notes, created_at, updated_at)
            VALUES (?, 'New', '', ?, ?)
            """,
            (job_id, now, now),
        )
        return int(cur.lastrowid)


def update_application_status(
    job_id: int,
    status: str,
    db_path: Optional[Path] = None,
) -> None:
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    now = datetime.utcnow().isoformat() + "Z"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO applications
                (job_id, status, notes, created_at, updated_at)
            VALUES (?, ?, '', ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (job_id, status, now, now),
        )


def save_application_notes(
    job_id: int,
    notes: str,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    ensure_application_row(job_id, db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE applications SET notes = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (notes, now, job_id),
        )


def update_application_dates(
    job_id: int,
    applied_at: Optional[str] = None,
    next_action_date: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    ensure_application_row(job_id, db_path)
    sets = ["updated_at = ?"]
    params: List[Any] = [now]
    if applied_at is not None:
        sets.append("applied_at = ?")
        params.append(applied_at)
    if next_action_date is not None:
        sets.append("next_action_date = ?")
        params.append(next_action_date)
    params.append(job_id)
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE applications SET {', '.join(sets)} WHERE job_id = ?",
            params,
        )


def list_results(
    min_score: float = 0.0,
    source: Optional[str] = None,
    status: Optional[str] = None,
    remote_only: bool = False,
    search_text: str = "",
    hide_not_interested: bool = False,
    hide_applied: bool = False,
    search_run_id: Optional[int] = None,
    sort_by: str = "score",
    db_path: Optional[Path] = None,
) -> List[sqlite3.Row]:
    """
    Latest match per job (highest match_results.id) joined with job + app.
    """
    init_db(db_path)
    sort_by = sort_by if sort_by in ("score", "date", "title") else "score"
    order = {
        "score": "m.score DESC",
        "date": "j.discovered_at DESC",
        "title": "j.title COLLATE NOCASE ASC",
    }[sort_by]

    where = ["m.score >= ?"]
    params: List[Any] = [min_score]

    if source:
        where.append("j.source = ?")
        params.append(source)

    if status:
        if status == "New":
            where.append("(a.status IS NULL OR a.status = 'New')")
        else:
            where.append("a.status = ?")
            params.append(status)
    if hide_not_interested:
        where.append("(a.status IS NULL OR a.status != 'Not Interested')")
    if hide_applied:
        where.append("(a.status IS NULL OR a.status != 'Applied')")

    if remote_only:
        where.append(
            """
            (
                json_extract(j.raw_data, '$.remote') IN (1, 'true', 'True')
                OR instr(lower(ifnull(j.location,'')), 'remote') > 0
            )
            """
        )

    if search_text.strip():
        term = f"%{search_text.strip().lower()}%"
        where.append(
            """
            (
                lower(j.title) LIKE ? OR lower(j.company) LIKE ?
                OR lower(j.description) LIKE ?
            )
            """,
        )
        params.extend([term, term, term])

    run_filter = ""
    if search_run_id is not None:
        run_filter = "AND m.search_run_id = ?"
        params.append(search_run_id)

    where_sql = " AND ".join(where)

    sql = f"""
    WITH latest AS (
        SELECT mr.job_id, MAX(mr.id) AS mid
        FROM match_results mr
        GROUP BY mr.job_id
    )
    SELECT
        j.*,
        m.id AS match_id,
        m.search_run_id,
        m.score,
        m.grade,
        m.quality_band,
        m.matched_skills,
        m.missing_skills,
        m.matched_keywords,
        m.score_breakdown,
        m.created_at AS matched_at,
        a.id AS application_id,
        a.status AS application_status,
        a.notes AS application_notes,
        a.applied_at,
        a.next_action_date
    FROM latest
    INNER JOIN match_results m ON m.id = latest.mid
    INNER JOIN jobs j ON j.id = m.job_id
    LEFT JOIN applications a ON a.job_id = j.id
    WHERE {where_sql}
    {run_filter}
    ORDER BY {order}
    """
    with get_connection(db_path) as conn:
        return list(conn.execute(sql, params).fetchall())


def get_job_with_latest_match(
    job_id: int,
    db_path: Optional[Path] = None,
) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT j.*, m.*, a.status AS application_status, a.notes AS application_notes,
                   a.applied_at, a.next_action_date, a.id AS application_id
            FROM jobs j
            LEFT JOIN match_results m ON m.id = (
                SELECT id FROM match_results WHERE job_id = j.id
                ORDER BY id DESC LIMIT 1
            )
            LEFT JOIN applications a ON a.job_id = j.id
            WHERE j.id = ?
            """,
            (job_id,),
        ).fetchone()


def dashboard_metrics(db_path: Optional[Path] = None) -> dict:
    init_db(db_path)
    with get_connection(db_path) as conn:
        new_matches = conn.execute(
            """
            SELECT COUNT(DISTINCT j.id) FROM jobs j
            INNER JOIN match_results m ON m.job_id = j.id
            LEFT JOIN applications a ON a.job_id = j.id
            WHERE a.id IS NULL OR a.status IN ('New', 'Saved')
            """,
        ).fetchone()[0]
        saved = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Saved'",
        ).fetchone()[0]
        applied = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Applied'",
        ).fetchone()[0]
        sources_on = conn.execute(
            "SELECT COUNT(*) FROM job_sources WHERE enabled = 1",
        ).fetchone()[0]
    return {
        "new_matches": new_matches,
        "saved": saved,
        "applied": applied,
        "sources_enabled": sources_on,
    }


def dashboard_top_jobs(limit: int = 5, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    return list_results(
        min_score=0,
        hide_not_interested=True,
        hide_applied=True,
        sort_by="score",
        db_path=db_path,
    )[:limit]


def recently_saved_jobs(limit: int = 5, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT j.*, m.score, m.grade, m.quality_band,
                       a.status, a.updated_at
                FROM applications a
                INNER JOIN jobs j ON j.id = a.job_id
                LEFT JOIN match_results m ON m.id = (
                    SELECT id FROM match_results WHERE job_id = j.id
                    ORDER BY id DESC LIMIT 1
                )
                WHERE a.status = 'Saved'
                ORDER BY a.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall(),
        )


def list_applications_by_status(
    db_path: Optional[Path] = None,
) -> dict[str, List[sqlite3.Row]]:
    init_db(db_path)
    out: dict[str, List[sqlite3.Row]] = {s: [] for s in APPLICATION_STATUSES}
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT j.id AS job_id, j.*, m.score, m.grade, m.quality_band,
                   a.status, a.notes, a.applied_at, a.next_action_date, a.id AS app_id
            FROM applications a
            INNER JOIN jobs j ON j.id = a.job_id
            LEFT JOIN match_results m ON m.id = (
                SELECT id FROM match_results WHERE job_id = j.id
                ORDER BY id DESC LIMIT 1
            )
            ORDER BY a.updated_at DESC
            """,
        ).fetchall()
    for r in rows:
        st = r["status"] or "New"
        if st in out:
            out[st].append(r)
        else:
            out.setdefault(st, []).append(r)
    return out


def clear_old_match_results(
    keep_last_n_runs: int = 10,
    db_path: Optional[Path] = None,
) -> Tuple[int, int]:
    """Delete match_results (and optionally orphan jobs) for old runs."""
    init_db(db_path)
    deleted_m = 0
    with get_connection(db_path) as conn:
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM search_runs ORDER BY id DESC",
            ).fetchall()
        ]
        if len(ids) <= keep_last_n_runs:
            return (0, 0)
        drop_ids = ids[keep_last_n_runs:]
        placeholders = ",".join("?" * len(drop_ids))
        cur = conn.execute(
            f"DELETE FROM match_results WHERE search_run_id IN ({placeholders})",
            drop_ids,
        )
        deleted_m = cur.rowcount
        conn.execute(
            f"DELETE FROM search_runs WHERE id IN ({placeholders})",
            drop_ids,
        )
    return (deleted_m, len(drop_ids))


def export_match_results_rows(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT j.title, j.company, j.source, j.url, j.location,
                       m.score, m.grade, m.quality_band,
                       m.matched_skills, m.missing_skills
                FROM match_results m
                INNER JOIN jobs j ON j.id = m.job_id
                ORDER BY m.id DESC
                """,
            ).fetchall(),
        )


def export_applications_rows(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    with get_connection(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT a.status, a.notes, a.applied_at, a.next_action_date,
                       j.title, j.company, j.source, j.url
                FROM applications a
                INNER JOIN jobs j ON j.id = a.job_id
                ORDER BY a.updated_at DESC
                """,
            ).fetchall(),
        )


def export_saved_jobs_json(db_path: Optional[Path] = None) -> List[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT j.*, a.status, a.notes
            FROM applications a
            INNER JOIN jobs j ON j.id = a.job_id
            WHERE a.status = 'Saved'
            """,
        ).fetchall()
    return [dict(r) for r in rows]
