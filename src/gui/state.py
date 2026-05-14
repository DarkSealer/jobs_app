"""Streamlit session state helpers for Job Radar."""

from __future__ import annotations

from typing import Optional

import streamlit as st


def init_session_defaults() -> None:
    """One-time defaults for filter widgets."""
    if "results_job_id" not in st.session_state:
        st.session_state.results_job_id = None


def get_selected_job_id() -> Optional[int]:
    return st.session_state.get("results_job_id")


def set_selected_job_id(job_id: Optional[int]) -> None:
    st.session_state.results_job_id = job_id
