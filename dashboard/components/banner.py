"""Runtime-mode banner for the dashboard sidebar.

Renders a small banner whenever the dashboard is running on bundled sample
data. The check uses `src.utils.demo_data.is_sample_mode`, which inspects
the `.sample_mode` marker file written by `ensure_processed_data()`. The
marker persists across Streamlit Cloud session restarts (the filesystem
persists between requests, even though Python process state does not).
"""
from __future__ import annotations

import streamlit as st

from src.utils.demo_data import is_sample_mode


def render_sample_mode_banner() -> None:
    """If the runtime is in sample mode, render a sidebar info banner.

    Idempotent and cheap; safe to call at the top of every dashboard page.
    """
    if not is_sample_mode():
        return
    with st.sidebar:
        st.info(
            "**Runtime mode: bundled sample data.** "
            "No API calls are made at dashboard runtime. "
            "Run `make ingest && make features && make analysis` locally for fresh data."
        )
