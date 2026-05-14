"""Sources — enable boards and view health."""

from __future__ import annotations

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db

st.set_page_config(page_title="Job Radar — Sources", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Job sources")
st.caption(
    "Automated sources run from the Search page. "
    "LinkedIn, Glassdoor, and Upwork stay manual in Job Radar.",
)

with st.form("sources_form"):
    toggles = {}
    for r in db.list_sources():
        toggles[r["name"]] = st.checkbox(
            f"{r['name']} — {r['source_type']} — {r['status']}",
            value=bool(r["enabled"]),
            help=r["notes"] or "",
        )
    submitted = st.form_submit_button("Save source toggles")

if submitted:
    for name, en in toggles.items():
        db.update_source_enabled(name, en)
    st.success("Sources updated.")
    st.rerun()

st.subheader("Details")
for r in db.list_sources():
    st.write(
        f"**{r['name']}** ({r['source_type']}) — enabled={bool(r['enabled'])} — "
        f"{r['status']} — last check: {r['last_checked_at'] or '—'}",
    )
    if r["last_error"]:
        st.error(r["last_error"])
