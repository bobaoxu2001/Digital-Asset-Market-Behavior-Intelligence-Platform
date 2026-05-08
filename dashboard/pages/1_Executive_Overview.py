"""Executive Overview page - duplicates app.py landing for clearer navigation."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import drawdown_chart, indexed_price_chart, regime_timeline
from dashboard.components.insights import overview_insight
from dashboard.components.kpis import fmt_num, fmt_pct, kpi_row
from src.config import PROCESSED_DIR
from src.utils.demo_data import ensure_processed_data
from src.utils.io import read_json_safe, read_parquet_safe

# Cloud bootstrap: stage bundled sample parquets if the full pipeline has never run.
ensure_processed_data()

st.set_page_config(page_title="Executive Overview", layout="wide")
st.title("Executive Overview")
st.caption("Cross-asset state of the market — current regime, return / vol, sentiment, and DeFi liquidity at a glance.")

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
summary = read_json_safe(PROCESSED_DIR / "behavior_summary.json") or {}

if feats.empty:
    st.error("Run the pipeline first: `make ingest && make features && make analysis`.")
    st.stop()

all_assets = sorted(feats["asset"].unique())
default_assets = [a for a in ["BTC", "ETH", "SOL"] if a in all_assets] or all_assets[:3]
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
