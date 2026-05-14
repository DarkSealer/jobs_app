"""Dashboard — metrics and quick actions."""

from __future__ import annotations

import webbrowser

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db

st.set_page_config(page_title="Job Radar — Dashboard", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Dashboard")
m = db.dashboard_metrics()
c1, c2, c3, c4 = st.columns(4)
c1.metric("New matches", m["new_matches"])
c2.metric("Saved jobs", m["saved"])
c3.metric("Applied", m["applied"])
c4.metric("Sources enabled", m["sources_enabled"])

st.subheader("Top jobs to review today")
for row in db.dashboard_top_jobs(5):
    url = row["url"]
    with st.container():
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(
                f"**{row['title']}** @ {row['company']} — "
                f"{row['score']:.0f} ({row['quality_band'] or ''}) — "
                f"{row['source']}",
            )
        with col_b:
            if st.button("Open", key=f"do_{row['id']}"):
                if url:
                    webbrowser.open(url)
            if st.button("Save", key=f"ds_{row['id']}"):
                db.update_application_status(row["id"], "Saved")
                st.rerun()
            if st.button("Not interested", key=f"dn_{row['id']}"):
                db.update_application_status(row["id"], "Not Interested")
                st.rerun()

st.subheader("Recently saved")
for row in db.recently_saved_jobs(5):
    st.write(f"- {row['title']} @ {row['company']} ({row['source']})")

st.subheader("Last search")
last = db.get_last_search_run()
if last:
    st.json(
        {
            "finished_at": last["finished_at"],
            "status": last["status"],
            "total_found": last["total_found"],
            "total_matched": last["total_matched"],
            "error": last["error_message"],
        },
    )
else:
    st.info("No completed searches yet.")

st.subheader("Source health")
for s in db.list_sources():
    err = s["last_error"] or ""
    st.write(
        f"- **{s['name']}** — {s['status']} — "
        f"checked: {s['last_checked_at'] or '—'} "
        f"{('— error: ' + err) if err else ''}",
    )
