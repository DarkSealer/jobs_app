"""Settings — defaults, export, maintenance."""

from __future__ import annotations

import io
import json

import pandas as pd
import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db, reseed_sources_metadata, set_config_path

st.set_page_config(page_title="Job Radar — Settings", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Settings")

st.subheader("Defaults")
with st.form("defaults"):
    dlim = st.number_input(
        "Default result limit",
        10,
        200,
        int(db.get_setting("default_result_limit", "30")),
    )
    dmin = st.slider(
        "Default minimum score for searches",
        0.0,
        100.0,
        float(db.get_setting("default_min_score", "55")),
        1.0,
        help="Used on the Search page and for the “X at or above Y” summary.",
    )
    inbox_min = st.slider(
        "Default Results inbox score filter",
        0.0,
        100.0,
        float(db.get_setting("results_inbox_min_score", "0")),
        1.0,
        help="Initial value for the Results page slider (0 = show all saved jobs).",
    )
    cfg_path = st.text_input(
        "config.yaml path (relative to cwd or absolute)",
        value=db.get_setting("config_yaml_path", "config.yaml"),
    )
    if st.form_submit_button("Save settings"):
        db.set_setting("default_result_limit", str(int(dlim)))
        db.set_setting("default_min_score", str(dmin))
        db.set_setting("results_inbox_min_score", str(inbox_min))
        set_config_path(cfg_path)
        st.success("Saved.")
        st.rerun()

st.subheader("Export")
mr = db.export_match_results_rows()
if mr:
    dfm = pd.DataFrame([dict(r) for r in mr])
    buf = io.StringIO()
    dfm.to_csv(buf, index=False)
    st.download_button(
        "Download match results (CSV)",
        buf.getvalue(),
        file_name="match_results_export.csv",
        mime="text/csv",
    )
else:
    st.caption("No match rows to export.")

apps = db.export_applications_rows()
if apps:
    dfa = pd.DataFrame([dict(r) for r in apps])
    bufa = io.StringIO()
    dfa.to_csv(bufa, index=False)
    st.download_button(
        "Download applications (CSV)",
        bufa.getvalue(),
        file_name="applications_export.csv",
        mime="text/csv",
    )

saved_json = db.export_saved_jobs_json()
st.download_button(
    "Download saved jobs (JSON)",
    json.dumps(saved_json, indent=2, ensure_ascii=False),
    file_name="saved_jobs.json",
    mime="application/json",
)

st.subheader("Maintenance")
if st.button("Clear old search runs (keep last 10)"):
    dm, dr = db.clear_old_match_results(10)
    st.info(f"Removed {dm} match rows across {dr} runs.")

if st.button("Reinitialize source metadata (types / notes)"):
    reseed_sources_metadata()
    st.success("Sources metadata refreshed (toggles preserved).")
    st.rerun()
