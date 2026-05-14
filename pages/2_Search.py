"""Search — presets and run."""

from __future__ import annotations

import json

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db, run_search

st.set_page_config(page_title="Job Radar — Search", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Search")


def _split(s: str) -> list:
    return [p.strip() for p in s.split(",") if p.strip()]


presets = db.list_saved_searches()
preset_labels = ["(Custom)"] + [f"{r['id']}: {r['name']}" for r in presets]
choice = st.selectbox("Search preset", preset_labels)

role_kw = ""
locs = ""
remote_only = False
job_type = ""
min_score = float(db.get_setting("default_min_score", "55"))
res_limit = int(db.get_setting("default_result_limit", "30"))
enabled_src: list = []
excl = ""

if choice != "(Custom)":
    pid = int(choice.split(":")[0])
    row = db.get_saved_search(pid)
    if row:
        role_kw = ", ".join(json.loads(row["role_keywords"]))
        locs = ", ".join(json.loads(row["locations"]))
        remote_only = bool(row["remote_only"])
        job_type = row["job_type"] or ""
        min_score = float(row["minimum_score"])
        res_limit = int(row["result_limit"])
        enabled_src = json.loads(row["enabled_sources"])
        excl = ", ".join(json.loads(row["excluded_keywords"]))

st.info(
    "LinkedIn, Glassdoor, and Upwork are **manual** in Job Radar: "
    "they are never auto-scraped from this screen.",
)

role_keywords = st.text_input(
    "Role keywords (comma-separated)",
    value=role_kw or "Software Engineer, Developer",
)
locations = st.text_input(
    "Locations (comma-separated)",
    value=locs or "Remote",
)
c1, c2 = st.columns(2)
with c1:
    remote_only = st.checkbox("Remote only", value=remote_only)
with c2:
    job_type = st.text_input("Job type (optional)", value=job_type)

c3, c4 = st.columns(2)
with c3:
    minimum_score = st.slider("Minimum score", 0.0, 100.0, min_score, 1.0)
with c4:
    result_limit = st.number_input("Result limit", 10, 200, res_limit, 10)

src_rows = db.list_sources()
auto_src = [r["name"] for r in src_rows if r["name"] not in ("linkedin", "glassdoor", "upwork")]
default_sel = enabled_src if enabled_src else auto_src
sources_pick = st.multiselect(
    "Sources to include (automated only)",
    options=auto_src,
    default=[s for s in default_sel if s in auto_src],
)
excluded_keywords = st.text_input(
    "Excluded keywords (comma-separated)",
    value=excl,
)

col_save, col_run = st.columns(2)
with col_save:
    preset_name = st.text_input("Preset name (to save under)")
    if st.button("Save search preset") and preset_name.strip():
        db.create_saved_search(
            name=preset_name.strip(),
            role_keywords=_split(role_keywords),
            locations=_split(locations),
            remote_only=remote_only,
            job_type=job_type or None,
            minimum_score=minimum_score,
            enabled_sources=sources_pick,
            excluded_keywords=_split(excluded_keywords),
            result_limit=int(result_limit),
        )
        st.success("Preset saved.")
        st.rerun()

with col_run:
    run_clicked = st.button("Run search", type="primary")


if run_clicked:
    if not sources_pick:
        st.error("Select at least one automated source.")
    else:
        with st.status("Searching job boards…", expanded=True) as status:
            report = run_search(
                role_keywords=_split(role_keywords),
                locations=_split(locations),
                remote_only=remote_only,
                minimum_score=minimum_score,
                result_limit=int(result_limit),
                preset_enabled_sources=sources_pick,
                excluded_keywords=_split(excluded_keywords),
            )
            status.update(label="Done", state="complete")
        if report.error_message:
            st.error(report.error_message)
        st.success(
            f"Found **{report.total_found}** jobs, "
            f"**{report.total_matched}** at or above {minimum_score:.0f} "
            f"(search threshold). "
            f"Duration **{report.duration_seconds:.1f}s**.",
        )
        if report.total_found and report.total_found > report.total_matched:
            st.info(
                "Every scraped job is stored with a match score. "
                "Scores below your search threshold still appear on **Results** "
                "if you keep **Minimum score (filter)** at **0** (default). "
                "If that slider is higher (e.g. 55), weak matches are hidden "
                "even though they were found."
            )
        if report.total_found:
            st.page_link("pages/3_Results.py", label="Open Results inbox", icon="📥")
        if report.source_errors:
            st.warning("Some sources reported errors:")
            st.json(report.source_errors)
        st.write("Sources checked:", ", ".join(report.sources_registered))
