"""Reusable Streamlit UI pieces for Job Radar."""

from __future__ import annotations

from typing import List, Optional

import streamlit as st


def render_sidebar() -> None:
    """Left navigation for multipage Streamlit app."""
    st.sidebar.markdown("### Job Radar")
    st.sidebar.caption("Find better jobs faster")
    st.sidebar.divider()
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.page_link("pages/2_Search.py", label="Search", icon="🔎")
    st.sidebar.page_link("pages/3_Results.py", label="Results", icon="📥")
    st.sidebar.page_link("pages/4_Applications.py", label="Applications", icon="📋")
    st.sidebar.page_link("pages/5_Sources.py", label="Sources", icon="🌐")
    st.sidebar.page_link("pages/6_Profile.py", label="Profile", icon="👤")
    st.sidebar.page_link("pages/7_Settings.py", label="Settings", icon="⚙️")


def metric_row(items: List[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def quality_badge_html(score: float, band: Optional[str] = None) -> str:
    if band is None:
        if score >= 85:
            band = "Excellent"
        elif score >= 70:
            band = "Strong"
        elif score >= 55:
            band = "Maybe"
        else:
            band = "Weak"
    color = {
        "Excellent": "#1b7f3a",
        "Strong": "#2d8a5e",
        "Maybe": "#b8860b",
        "Weak": "#8b4513",
    }.get(band, "#555")
    return f'<span style="color:{color};font-weight:600;">{band}</span> ({score:.0f})'
