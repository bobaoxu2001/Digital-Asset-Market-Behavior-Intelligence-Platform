"""Runtime-mode banner for the dashboard sidebar.

Renders a small banner whenever the dashboard is running on bundled sample
data. The check uses ``src.utils.demo_data.is_sample_mode``, which inspects
the ``.sample_mode`` marker file written by ``ensure_processed_data()`` and
also detects hosted-runtime environment variables. The marker persists
across Streamlit Cloud session restarts.

This module is defensive: any import or runtime error is caught so a banner
problem can never crash the dashboard.
"""
from __future__ import annotations

import streamlit as st

# Defensive import: if the helper module is unavailable for any reason, fall
# back to a no-op so the dashboard still loads.
try:
    from src.utils.demo_data import is_sample_mode  # noqa: F401
except Exception:  # pragma: no cover - defensive only
    def is_sample_mode(*_args, **_kwargs) -> bool:  # type: ignore[misc]
        return False


def render_sample_mode_banner() -> None:
    """If the runtime is in sample mode, render a sidebar info banner.

    Idempotent and cheap; safe to call at the top of every dashboard page.
    Any unexpected error is suppressed so the banner cannot crash the page.
    """
    try:
        active = bool(is_sample_mode())
    except Exception:
        active = False
    if not active:
        return
    try:
        with st.sidebar:
            st.info(
                "**Runtime mode: bundled sample data.** "
                "No API calls are made at dashboard runtime. "
                "Run `make ingest && make features && make analysis` locally for fresh data."
            )
    except Exception:
        # Never let a banner failure surface as a page error.
        return
