"""Liquidity & DeFi Participation page."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import liquidity_stress_chart, tvl_chart
from dashboard.components.insights import liquidity_takeaway
from dashboard.components.kpis import fmt_num, fmt_pct, kpi_row
from dashboard.components.banner import render_sample_mode_banner
from dashboard.components.layout import apply_institutional_theme, render_analyst_takeaway, render_page_header, render_sidebar_context
from src.config import PROCESSED_DIR
from src.utils.demo_data import ensure_processed_data
from src.utils.io import read_parquet_safe

ensure_processed_data()

st.set_page_config(page_title="Liquidity & DeFi Participation", layout="wide")
apply_institutional_theme()
render_sample_mode_banner()
render_page_header(
    "Liquidity & DeFi Participation",
    "Chain TVL, stablecoin supply, protocol concentration, and a composite liquidity-stress monitor.",
)

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
chain_view = read_parquet_safe(PROCESSED_DIR / "chain_tvl_view.parquet")
proto = read_parquet_safe(PROCESSED_DIR / "defi_protocol_tvl.parquet")
stables = read_parquet_safe(PROCESSED_DIR / "stablecoins.parquet")

if feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

render_sidebar_context(
    "Liquidity signal",
    [
        "Liquidity stress is a composite of negative TVL trend and stablecoin contraction.",
        "TVL is USD-denominated, so price effects and capital-flow effects should be separated in discussion.",
        "A +1.5 score marks stress; below-threshold readings are monitoring signals, not all-clear guarantees.",
    ],
)

cur = feats.drop_duplicates("date").sort_values("date").iloc[-1]
items = [
    ("Total DeFi TVL", fmt_num(cur.get("tvl_usd"))),
    ("TVL 7d", fmt_pct(cur.get("tvl_7d_change_pct"))),
    ("TVL 30d", fmt_pct(cur.get("tvl_30d_change_pct"))),
    ("Stablecoin supply", fmt_num(cur.get("stable_total_usd"))),
    ("Stablecoin 7d", fmt_pct(cur.get("stablecoin_7d_change_pct"))),
    ("Liquidity stress", f"{(cur.get('liquidity_stress_score') or 0):+.2f}"),
]
kpi_row(items)

if not chain_view.empty:
    st.plotly_chart(tvl_chart(chain_view), width="stretch")

st.plotly_chart(liquidity_stress_chart(feats), width="stretch")

# Top-10 protocols by latest TVL
if not proto.empty:
    latest_date = proto["date"].max()
    latest = proto[proto["date"] == latest_date].sort_values("tvl_usd", ascending=False).head(10)
    fig = go.Figure(go.Bar(x=latest["tvl_usd"], y=latest["protocol"], orientation="h", marker_color="#5B8FF9"))
    fig.update_layout(template="plotly_dark", title=f"Top protocols by TVL (as of {latest_date.date()})",
                      height=380, margin=dict(l=10, r=10, t=40, b=10), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch")

# Stablecoin supply chart
if not stables.empty:
    fig = go.Figure(go.Scatter(x=stables["date"], y=stables["stable_total_usd"], mode="lines", line=dict(color="#5AD8A6")))
    fig.update_layout(template="plotly_dark", title="Stablecoin total circulating supply (USD)",
                      height=320, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")

render_analyst_takeaway(*liquidity_takeaway(feats))
