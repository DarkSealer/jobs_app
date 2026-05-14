"""Results — inbox, filters, detail, actions."""

from __future__ import annotations

import json
import webbrowser
from datetime import date

import streamlit as st

from src.gui import database as db
from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import build_why_and_risks, init_gui_db

st.set_page_config(page_title="Job Radar — Results", layout="wide")
init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.header("Results inbox")

min_score = st.slider(
    "Minimum score (filter)",
    0.0,
    100.0,
    float(db.get_setting("results_inbox_min_score", "0")),
    1.0,
    help=(
        "Hide jobs scored below this value. Default is 0 so every saved "
        "match appears. Raise it to focus on stronger fits (e.g. 55). "
        "This is separate from the minimum score used when you *run* a search."
    ),
)
src_rows = db.list_sources()
src_names = sorted({r["name"] for r in src_rows})
source_f = st.selectbox("Source", ["(all)"] + src_names)
status_opts = ["(all)"] + list(db.APPLICATION_STATUSES)
status_f = st.selectbox("Status", status_opts)
remote_only = st.checkbox("Remote only", value=False)
search_txt = st.text_input("Search text (title / company / description)")
hide_ni = st.checkbox("Hide Not Interested", value=True)
hide_ap = st.checkbox("Hide Applied", value=False)
sort_by = st.selectbox("Sort by", ["score", "date", "title"])

rows = db.list_results(
    min_score=min_score,
    source=None if source_f == "(all)" else source_f,
    status=None if status_f == "(all)" else status_f,
    remote_only=remote_only,
    search_text=search_txt,
    hide_not_interested=hide_ni,
    hide_applied=hide_ap,
    sort_by=sort_by,
)

st.caption(f"{len(rows)} job(s)")

for row in rows:
    jid = row["id"]
    ms = row["matched_skills"]
    if isinstance(ms, str):
        try:
            ms = json.loads(ms)
        except json.JSONDecodeError:
            ms = []
    miss = row["missing_skills"]
    if isinstance(miss, str):
        try:
            miss = json.loads(miss)
        except json.JSONDecodeError:
            miss = []
    bd = row["score_breakdown"]
    if isinstance(bd, str):
        try:
            bd = json.loads(bd)
        except json.JSONDecodeError:
            bd = {}

    raw = {}
    try:
        raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
    except json.JSONDecodeError:
        raw = {}

    title_match = float(bd.get("title_score", 0)) * 100 if isinstance(bd, dict) else 0.0

    summary = {
        "score": row["score"],
        "matched_skills": ms,
        "missing_skills": miss,
        "title_match": title_match,
        "remote": bool(raw.get("remote")),
        "salary": row["salary"] or "",
        "location": row["location"],
        "score_breakdown": bd,
    }

    why, risks = build_why_and_risks(summary, min_score)
    desc = (row["description"] or "")[:280]

    with st.expander(
        f"{row['title']} @ {row['company']} — {row['score']:.0f} "
        f"({row['quality_band'] or ''})",
    ):
        st.markdown(f"**Source:** {row['source']} | **Location:** {row['location']}")
        if row["salary"]:
            st.markdown(f"**Salary:** {row['salary']}")
        st.markdown(f"**URL:** {row['url']}")
        st.markdown(f"**Matched skills:** {', '.join(ms[:12])}")
        st.markdown(f"**Missing skills:** {', '.join(miss[:10])}")
        st.markdown("**Preview:** " + desc + ("…" if len(row["description"] or "") > 280 else ""))

        st.subheader("Why this matches")
        for w in why or ["(No strong signals beyond the raw score.)"]:
            st.write(f"- {w}")
        st.subheader("Risks")
        for r in risks or ["(No extra risks flagged.)"]:
            st.write(f"- {r}")

        st.subheader("Score breakdown")
        st.json(bd if bd else {})

        notes_val = row["application_notes"] or ""
        notes = st.text_area("Notes", value=notes_val, key=f"n_{jid}")
        st_date = st.date_input(
            "Next action",
            value=None,
            key=f"d_{jid}",
        )
        cur_st = row["application_status"] or "New"
        try:
            st_idx = db.APPLICATION_STATUSES.index(cur_st)
        except ValueError:
            st_idx = 0
        new_status = st.selectbox(
            "Status",
            db.APPLICATION_STATUSES,
            index=st_idx,
            key=f"s_{jid}",
        )

        b1, b2, b3, b4, b5, b6 = st.columns(6)
        if b1.button("Open", key=f"o_{jid}"):
            if row["url"]:
                webbrowser.open(row["url"])
        if b2.button("Save", key=f"sv_{jid}"):
            db.update_application_status(jid, "Saved")
            st.rerun()
        if b3.button("Apply today", key=f"at_{jid}"):
            db.update_application_status(jid, "Apply Today")
            st.rerun()
        if b4.button("Applied", key=f"ap_{jid}"):
            db.update_application_status(jid, "Applied")
            db.update_application_dates(
                jid,
                applied_at=date.today().isoformat(),
                db_path=None,
            )
            st.rerun()
        if b5.button("Not interested", key=f"ni_{jid}"):
            db.update_application_status(jid, "Not Interested")
            st.rerun()
        if b6.button("Update notes/status", key=f"up_{jid}"):
            db.save_application_notes(jid, notes)
            db.update_application_status(jid, new_status)
            if st_date:
                db.update_application_dates(
                    jid,
                    next_action_date=st_date.isoformat(),
                    db_path=None,
                )
            st.rerun()
