"""KPI rendering helpers.

All formatters return ``"N/A"`` for any of the following:
    - ``None``
    - ``float('nan')`` (including pandas ``NA``-coerced floats)
    - ``float('inf')`` / ``-float('inf')``
    - any value that fails to coerce to ``float``

Real ``0`` values are preserved. The dashboard relies on this contract so a
sample-mode KPI never displays ``"+nan"``, ``"inf"``, or a misleading zero
that originated from a missing source column.
"""
from __future__ import annotations

import math
from typing import Any, Optional

import streamlit as st

NA_TEXT = "N/A"


def _to_float(x: Any) -> Optional[float]:
    """Return ``float(x)`` or ``None`` if x is null / non-finite / not numeric."""
    if x is None:
        return None
    try:
        # pandas ``NA`` raises on float() — handle defensively
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def fmt_pct(x: Any) -> str:
    v = _to_float(x)
    if v is None:
        return NA_TEXT
    return f"{v*100:+.1f}%"


def fmt_num(x: Any, decimals: int = 2) -> str:
    v = _to_float(x)
    if v is None:
        return NA_TEXT
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.2f}M"
    return f"{v:,.{decimals}f}"


def fmt_signed(x: Any, decimals: int = 2) -> str:
    """Signed float (e.g. activity index, z-scores, stress score)."""
    v = _to_float(x)
    if v is None:
        return NA_TEXT
    return f"{v:+.{decimals}f}"


def fmt_int(x: Any) -> str:
    """Integer-style KPI (e.g. transaction count, address count)."""
    v = _to_float(x)
    if v is None:
        return NA_TEXT
    return f"{int(v):,}"


def kpi_row(items: list[tuple[str, str]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.metric(label, value)
