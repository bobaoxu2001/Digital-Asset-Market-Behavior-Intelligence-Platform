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

from dashboard.components.insights import overview_takeaway  # noqa: E402
from dashboard.components.kpis import fmt_pct, fmt_signed, kpi_row  # noqa: E402
from dashboard.components.charts import (  # noqa: E402
    drawdown_chart,
    indexed_price_chart,
    market_breadth_chart,
    regime_timeline,
)
from dashboard.components.layout import (  # noqa: E402
    apply_institutional_theme,
    render_analyst_takeaway,
    render_demo_flow,
    render_page_header,
    render_sidebar_context,
)
from dashboard.components.banner import render_sample_mode_banner  # noqa: E402
from src.utils.io import read_json_safe, read_parquet_safe  # noqa: E402
from src.config import PROCESSED_DIR  # noqa: E402
from src.utils.demo_data import ensure_processed_data  # noqa: E402

# Cloud bootstrap: if processed data is missing (e.g. on Streamlit Cloud where
# the ingestion pipeline never ran), stage the bundled sample parquets so every
# page renders. Idempotent and safe locally.
ensure_processed_data()

st.set_page_config(
    page_title="Digital Asset Market Behavior Intelligence",
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
    apply_institutional_theme()
    render_sample_mode_banner()
    render_page_header(
        "Digital Asset Market Behavior Intelligence Platform",
        "An institutional-style research terminal for crypto market behavior: price, realized volatility, "
        "liquidity stress, DeFi participation, sentiment confirmation, on-chain activity, and event reactions.",
        "What If Capital role-aligned portfolio project",
    )

    feats = load_features()
    summary = load_summary() or {}

    if feats.empty:
        st.error("No processed features found. Run `make ingest && make features && make analysis` first.")
        st.stop()

    # Sidebar global filters
    all_assets = sorted(feats["asset"].unique())
    default_assets = [a for a in ["BTC", "ETH", "SOL"] if a in all_assets] or all_assets[:3]
    render_sidebar_context(
        "Demo context",
        [
            "Dashboard reads processed parquet only; no live API calls are made at runtime.",
            "Sample mode is disclosed explicitly so analysis is reproducible and not overstated.",
            "Use Strategy Insights, Sentiment, and Liquidity pages for the 3-minute interview story.",
        ],
    )
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
    st.subheader("Market State Snapshot")

    per = summary.get("per_asset", {}) if summary else {}
    btc = per.get("BTC", {})
    items = [
        ("BTC regime", btc.get("regime", "—")),
        ("BTC vol regime", btc.get("volatility_regime", "—")),
        ("BTC 30d return", fmt_pct(btc.get("ret_30d"))),
        ("BTC drawdown", fmt_pct(btc.get("drawdown"))),
        ("Fear & Greed", str(int(summary.get("sentiment_score", 0))) if summary else "—"),
        ("Breadth 7d", fmt_pct(summary.get("market_breadth_positive_7d"))),
        ("Liq. stress", fmt_signed(summary.get("current_liquidity_stress_score"))),
    ]
    kpi_row(items)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(indexed_price_chart(sub, assets), width="stretch")
    with col2:
        st.plotly_chart(drawdown_chart(sub, assets), width="stretch")

    st.plotly_chart(market_breadth_chart(sub), width="stretch")

    if "BTC" in assets:
        st.plotly_chart(regime_timeline(sub, "BTC"), width="stretch")

    render_analyst_takeaway(*overview_takeaway(feats, summary))

    render_demo_flow()

    st.markdown(
        "Use the left sidebar to switch pages: **Market Regime & Volatility**, "
        "**Sentiment & Event Reaction**, **Liquidity & DeFi Participation**, "
        "**On-chain Activity**, **Strategy Insights**."
    )


if __name__ == "__main__":
    main()
