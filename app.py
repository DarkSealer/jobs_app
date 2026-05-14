"""
Job Radar — Streamlit entry (Home).

Run from the project root:

    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src.gui import state as gui_state
from src.gui.components import render_sidebar
from src.gui.services import init_gui_db

st.set_page_config(
    page_title="Job Radar",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_gui_db()
gui_state.init_session_defaults()
render_sidebar()

st.title("Job Radar")
st.caption("Find better jobs faster")
st.markdown(
    """
Welcome. Use the sidebar to:

- **Dashboard** — quick metrics and top jobs to review
- **Search** — run a multi-board search
- **Results** — inbox, filters, and actions
- **Applications** — track status over time
- **Sources** — enable or disable boards (manual sources are never auto-scraped)
- **Profile** — your matching profile
- **Settings** — defaults, exports, maintenance

The CLI (`python main.py search`) still works alongside this UI.
""",
)
