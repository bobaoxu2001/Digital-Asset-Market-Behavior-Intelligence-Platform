"""Strategy Insights page - the analyst-style synthesis."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import event_impact_bar, event_type_heatmap
from dashboard.components.insights import strategy_insight
from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe

st.set_page_config(page_title="Strategy Insights", layout="wide")
st.title("Strategy Insights")

es = read_parquet_safe(PROCESSED_DIR / "event_study.parquet")
typeasset = read_parquet_safe(PROCESSED_DIR / "event_study_typeasset.parquet")
regime_cond = read_parquet_safe(PROCESSED_DIR / "regime_conditional.parquet")
feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")

if es.empty or feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

st.subheader("Top 10 most impactful events")
st.plotly_chart(event_impact_bar(es, top_n=10), use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Event-type x asset impact heatmap")
    st.plotly_chart(event_type_heatmap(typeasset), use_container_width=True)
with col2:
    st.subheader("Mean impact by event type")
    by_type = es.groupby("event_type")["impact_score"].mean().sort_values(ascending=False).reset_index()
    fig = px.bar(by_type, x="event_type", y="impact_score", template="plotly_dark", color_discrete_sequence=["#9270CA"])
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Regime-conditional return distribution")
if not regime_cond.empty:
    fig = px.bar(
        regime_cond, x="regime", y="annualized_return", color="asset", barmode="group",
        template="plotly_dark", title="Annualized return by regime (per asset)",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(regime_cond.round(4), use_container_width=True)

st.subheader("Top 10 unusual recent days (volume spike + abnormal on-chain or |return|>5%)")
recent = feats[feats["date"] >= feats["date"].max() - pd.Timedelta(days=180)]
unusual = recent[
    (recent["volume_spike_flag"] == 1)
    | (recent["abnormal_onchain_activity_flag"] == 1)
    | (recent["daily_return"].abs() > 0.05)
].sort_values("daily_return", key=lambda s: s.abs(), ascending=False).head(10)
if not unusual.empty:
    cols = ["date", "asset", "regime", "daily_return", "rolling_30d_volatility",
            "sentiment_score", "liquidity_stress_score", "onchain_activity_index"]
    show_cols = [c for c in cols if c in unusual.columns]
    st.dataframe(unusual[show_cols].round(4), use_container_width=True)

st.info(strategy_insight(es, regime_cond))

st.markdown("---")
st.markdown(
    "**What happened?** Event-driven and macro-shock days dominate the impact ranking, with DeFi-token "
    "exposures amplifying regulatory and ETF news.\n\n"
    "**Why it matters?** Regime-conditional returns make it clear that being mechanically long through "
    "*Risk-off* and *Liquidity Stress* periods has historically been costly; *Momentum* and *Calm* deliver "
    "the bulk of positive risk-adjusted returns.\n\n"
    "**What to monitor next?** Liquidity stress score and abnormal on-chain activity flags **before** "
    "scheduled macro events (FOMC/CPI). Their co-occurrence has historically predicted extension rather "
    "than mean-reversion of event reactions."
)
