"""Market Regime & Volatility page."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import drawdown_chart, regime_distribution, regime_timeline, vol_chart
from dashboard.components.insights import regime_insight
from dashboard.components.kpis import fmt_pct, kpi_row
from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe

st.set_page_config(page_title="Market Regime & Volatility", layout="wide")
st.title("Market Regime & Volatility")

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
if feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

all_assets = sorted(feats["asset"].unique())
default_assets = [a for a in ["BTC", "ETH", "SOL"] if a in all_assets]
with st.sidebar:
    assets = st.multiselect("Assets", all_assets, default=default_assets)
    asset_focus = st.selectbox("Focus asset", assets if assets else all_assets, index=0)
    date_min, date_max = feats["date"].min().date(), feats["date"].max().date()
    dr = st.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
start, end = (dr if isinstance(dr, tuple) and len(dr) == 2 else (date_min, date_max))

sub = feats[(feats["asset"].isin(assets)) & (feats["date"] >= str(start)) & (feats["date"] <= str(end))]

g = feats[feats["asset"] == asset_focus].sort_values("date")
last90 = g.tail(90)
top_regime = last90["regime"].value_counts().idxmax() if not last90.empty else "—"
transitions = int((last90["regime"] != last90["regime"].shift()).sum() - 1) if not last90.empty else 0
cur_vol = (g["rolling_30d_volatility"].iloc[-1] if not g.empty else 0) or 0
cur_dd = (g["drawdown"].iloc[-1] if not g.empty else 0) or 0

items = [
    (f"{asset_focus} dominant regime (90d)", top_regime),
    ("Regime transitions (90d)", str(transitions)),
    ("Current 30d vol", fmt_pct(cur_vol)),
    ("Current drawdown", fmt_pct(cur_dd)),
]
kpi_row(items)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(vol_chart(sub, asset_focus), use_container_width=True)
with col2:
    st.plotly_chart(drawdown_chart(sub, assets), use_container_width=True)

st.plotly_chart(regime_timeline(sub, asset_focus), use_container_width=True)
st.plotly_chart(regime_distribution(sub, assets), use_container_width=True)

st.subheader("Regime transition matrix (last 365 days, focus asset)")
gtail = g.tail(365)
if not gtail.empty:
    transitions_df = pd.crosstab(gtail["regime"], gtail["regime"].shift(-1).fillna("(end)"))
    st.dataframe(transitions_df, use_container_width=True)

st.info(regime_insight(feats, asset_focus))
