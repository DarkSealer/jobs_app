"""Applications — simple Kanban-style tracker."""

from __future__ import annotations

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db

st.set_page_config(page_title="Job Radar — Applications", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Applications")

KANBAN_STATUSES = [
    "Saved",
    "Apply Today",
    "Applied",
    "Interview",
    "Rejected",
    "Ghosted",
]

by_status = db.list_applications_by_status()
cols = st.columns(len(KANBAN_STATUSES))
for col, status in zip(cols, KANBAN_STATUSES):
    with col:
        st.subheader(status)
        for row in by_status.get(status, []):
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['company']} · {row['source']}")
            if row["score"] is not None:
                st.caption(f"Score: {row['score']:.0f}")
            new_st = st.selectbox(
                "Move to",
                db.APPLICATION_STATUSES,
                key=f"k_{status}_{row['app_id']}",
                label_visibility="collapsed",
            )
            if st.button("Update", key=f"bu_{status}_{row['app_id']}"):
                db.update_application_status(row["job_id"], new_st)
                st.rerun()

st.divider()
st.subheader("All statuses (including New / Not Interested)")
for status_name in db.APPLICATION_STATUSES:
    rows = by_status.get(status_name, [])
    if not rows:
        continue
    with st.expander(f"{status_name} ({len(rows)})"):
        for row in rows:
            st.write(
                f"- {row['title']} @ {row['company']} — "
                f"{row['source']} — applied: {row['applied_at'] or '—'}",
            )
