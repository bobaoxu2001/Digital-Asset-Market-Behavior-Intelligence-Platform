"""KPI rendering helpers."""
from __future__ import annotations

import streamlit as st


def fmt_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and (x != x)):
        return "—"
    return f"{x*100:+.1f}%"


def fmt_num(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and (x != x)):
        return "—"
    if abs(x) >= 1e9:
        return f"${x/1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x/1e6:,.2f}M"
    return f"{x:,.{decimals}f}"


def kpi_row(items: list[tuple[str, str]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.metric(label, value)
