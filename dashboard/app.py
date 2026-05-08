"""Digital Asset Market Behavior Intelligence Platform - Streamlit entry point.

Loads only processed parquet files. No live API calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure repo root is on sys.path when running via `streamlit run dashboard/app.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.insights import overview_insight  # noqa: E402
from dashboard.components.kpis import fmt_num, fmt_pct, kpi_row  # noqa: E402
from dashboard.components.charts import (  # noqa: E402
    drawdown_chart,
    indexed_price_chart,
    regime_timeline,
)
from src.utils.io import read_json_safe, read_parquet_safe  # noqa: E402
from src.config import PROCESSED_DIR  # noqa: E402

st.set_page_config(
    page_title="Digital Asset Market Behavior Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_features():
    return read_parquet_safe(PROCESSED_DIR / "features.parquet")


@st.cache_data(show_spinner=False)
def load_summary():
    return read_json_safe(PROCESSED_DIR / "behavior_summary.json")


def main():
    st.title("Digital Asset Market Behavior Intelligence Platform")
    st.caption("A behavior-explanation platform for crypto markets — regimes, events, sentiment, liquidity, on-chain.")

    feats = load_features()
    summary = load_summary() or {}

    if feats.empty:
        st.error("No processed features found. Run `make ingest && make features && make analysis` first.")
        st.stop()

    # Sidebar global filters
    all_assets = sorted(feats["asset"].unique())
    default_assets = [a for a in ["BTC", "ETH", "SOL"] if a in all_assets] or all_assets[:3]
    with st.sidebar:
        st.header("Filters")
        assets = st.multiselect("Assets", all_assets, default=default_assets, key="g_assets")
        date_min = feats["date"].min().date()
        date_max = feats["date"].max().date()
        dr = st.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max, key="g_dates")

    if isinstance(dr, tuple) and len(dr) == 2:
        start, end = dr
    else:
        start, end = date_min, date_max

    sub = feats[(feats["asset"].isin(assets)) & (feats["date"] >= str(start)) & (feats["date"] <= str(end))]

    # Executive overview content lives here on the home page
    st.subheader("Executive Overview")

    per = summary.get("per_asset", {}) if summary else {}
    btc = per.get("BTC", {})
    items = [
        ("BTC regime", btc.get("regime", "—")),
        ("BTC 30d return", fmt_pct(btc.get("ret_30d"))),
        ("BTC 30d vol", fmt_pct(btc.get("vol_30d"))),
        ("Fear & Greed", str(int(summary.get("sentiment_score", 0))) if summary else "—"),
        ("DeFi TVL", fmt_num(summary.get("current_tvl_usd"))),
        ("Liq. stress", f"{(summary.get('current_liquidity_stress_score') or 0):+.2f}"),
    ]
    kpi_row(items)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(indexed_price_chart(sub, assets), use_container_width=True)
    with col2:
        st.plotly_chart(drawdown_chart(sub, assets), use_container_width=True)

    if "BTC" in assets:
        st.plotly_chart(regime_timeline(sub, "BTC"), use_container_width=True)

    st.info(overview_insight(feats, summary))

    st.markdown(
        "Use the left sidebar to switch pages: **Market Regime & Volatility**, "
        "**Sentiment & Event Reaction**, **Liquidity & DeFi Participation**, "
        "**On-chain Activity**, **Strategy Insights**."
    )


if __name__ == "__main__":
    main()
