"""Executive Overview page - duplicates app.py landing for clearer navigation."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.banner import render_sample_mode_banner
from dashboard.components.charts import drawdown_chart, indexed_price_chart, market_breadth_chart, regime_timeline
from dashboard.components.insights import overview_takeaway
from dashboard.components.kpis import fmt_pct, fmt_signed, kpi_row
from dashboard.components.layout import (
    apply_institutional_theme,
    render_analyst_takeaway,
    render_demo_flow,
    render_page_header,
    render_sidebar_context,
)
from src.config import PROCESSED_DIR
from src.utils.demo_data import ensure_processed_data
from src.utils.io import read_json_safe, read_parquet_safe

# Cloud bootstrap: stage bundled sample parquets if the full pipeline has never run.
ensure_processed_data()

st.set_page_config(page_title="Executive Overview", layout="wide")
apply_institutional_theme()
render_sample_mode_banner()
render_page_header(
    "Executive Overview",
    "A first-screen market read: regime, drawdown, sentiment, cross-asset participation, and liquidity stress.",
)

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
summary = read_json_safe(PROCESSED_DIR / "behavior_summary.json") or {}

if feats.empty:
    st.error("Run the pipeline first: `make ingest && make features && make analysis`.")
    st.stop()

all_assets = sorted(feats["asset"].unique())
default_assets = [a for a in ["BTC", "ETH", "SOL"] if a in all_assets] or all_assets[:3]
render_sidebar_context(
    "How to read this page",
    [
        "Breadth shows whether the move is broad risk-on/risk-off or isolated asset behavior.",
        "Liquidity stress combines DeFi TVL and stablecoin contraction; +1.5 is the stress threshold.",
        "The page is descriptive and uses only processed parquet loaded at runtime.",
    ],
)
with st.sidebar:
    assets = st.multiselect("Assets", all_assets, default=default_assets)
    date_min, date_max = feats["date"].min().date(), feats["date"].max().date()
    dr = st.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
start, end = (dr if isinstance(dr, tuple) and len(dr) == 2 else (date_min, date_max))

sub = feats[(feats["asset"].isin(assets)) & (feats["date"] >= str(start)) & (feats["date"] <= str(end))]

per = summary.get("per_asset", {})
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
