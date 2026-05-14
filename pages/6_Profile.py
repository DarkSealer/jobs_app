"""Profile — edit matching profile."""

from __future__ import annotations

import json

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import compute_profile_strength, init_gui_db

st.set_page_config(page_title="Job Radar — Profile", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Profile")
row = db.get_or_create_default_profile()

with st.form("profile_form"):
    name = st.text_input("Name", value=row.name)
    email = st.text_input("Email", value=row.email)
    summary = st.text_area("Summary", value=row.summary, height=160)
    years = st.number_input("Years of experience", 0, 60, int(row.years_experience))
    skills = st.text_input(
        "Skills (comma-separated)",
        value=", ".join(row.skills),
    )
    titles = st.text_input(
        "Target job titles (comma-separated)",
        value=", ".join(row.target_titles),
    )
    locs = st.text_input(
        "Preferred locations (comma-separated)",
        value=", ".join(row.locations),
    )
    remote_only = st.checkbox("Remote only", value=row.remote_only)
    min_sal = st.number_input(
        "Minimum salary (annual, optional)",
        min_value=0,
        value=int(row.minimum_salary or 0),
        step=1000,
    )
    excl = st.text_input(
        "Excluded keywords (comma-separated)",
        value=", ".join(row.excluded_keywords),
    )
    projects_json = st.text_area(
        "Projects (JSON list of {name, description, technologies[], url?})",
        value=json.dumps(row.projects, indent=2, ensure_ascii=False)
        if row.projects
        else "[]",
        height=200,
    )
    save = st.form_submit_button("Save profile")

if save:
    try:
        projects = json.loads(projects_json) if projects_json.strip() else []
        if not isinstance(projects, list):
            raise ValueError("Projects must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        st.error(f"Invalid projects JSON: {e}")
    else:
        def _split(s: str) -> list:
            return [p.strip() for p in s.split(",") if p.strip()]

        db.save_profile(
            row.id,
            name=name,
            email=email,
            summary=summary,
            years_experience=int(years),
            skills=_split(skills),
            target_titles=_split(titles),
            locations=_split(locs),
            remote_only=remote_only,
            minimum_salary=int(min_sal) if min_sal > 0 else None,
            excluded_keywords=_split(excl),
            projects=projects,
        )
        st.success("Profile saved.")
        st.rerun()

row2 = db.get_or_create_default_profile()
score, hints = compute_profile_strength(row2)
st.metric("Profile strength", f"{score} / 100")
if hints:
    st.subheader("Suggestions")
    for h in hints:
        st.write(f"- {h}")
