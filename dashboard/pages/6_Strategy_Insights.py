"""Strategy Insights page - the analyst-style synthesis."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import asset_rotation_chart, event_impact_bar, event_type_heatmap, market_breadth_chart
from dashboard.components.insights import strategy_takeaway
from dashboard.components.banner import render_sample_mode_banner
from dashboard.components.layout import apply_institutional_theme, render_analyst_takeaway, render_page_header, render_sidebar_context
from src.config import PROCESSED_DIR
from src.utils.demo_data import ensure_processed_data
from src.utils.io import read_parquet_safe

ensure_processed_data()

st.set_page_config(page_title="Strategy Insights", layout="wide")
apply_institutional_theme()
render_sample_mode_banner()
render_page_header(
    "Strategy Insights",
    "A monitoring framework for catalyst sensitivity, regime-conditioned behavior, and cross-asset rotation. Not trading advice.",
)

with st.expander("Methodology note — impact score and non-causal interpretation"):
    st.markdown(
        "**Composite impact score** = `|cum_log_return(t, t+7)|` + `max(realized_vol_post / realized_vol_pre − 1, 0)`. "
        "It captures both directional move and volatility expansion in a single non-negative number. "
        "Severity from the curated calendar is **not** used as a weight, so subjectivity in the rubric "
        "does not drive the ranking.\n\n"
        "**Interpretation.** These figures are short-window market reactions associated with each event "
        "category. They are descriptive, not strict causal estimates: other contemporaneous information "
        "may have moved markets in the same window. ETF and CPI events show lower average short-window "
        "impact in this sample, likely because many were anticipated before the event date or close to "
        "consensus expectations — that does not mean those events are unimportant; it means the measured "
        "event-window surprise was smaller."
    )

es = read_parquet_safe(PROCESSED_DIR / "event_study.parquet")
typeasset = read_parquet_safe(PROCESSED_DIR / "event_study_typeasset.parquet")
regime_cond = read_parquet_safe(PROCESSED_DIR / "regime_conditional.parquet")
feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")

if es.empty or feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

render_sidebar_context(
    "Strategy lens",
    [
        "Impact score ranks short-window reaction, not causal importance.",
        "Alt/DeFi beta behavior is separated from BTC/ETH/SOL majors to show rotation.",
        "Use this page to discuss what to monitor before macro, ETF, protocol, and exploit events.",
    ],
)

st.subheader("Top 10 most impactful events")
st.plotly_chart(event_impact_bar(es, top_n=10), width="stretch")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Event-type x asset impact heatmap")
    st.plotly_chart(event_type_heatmap(typeasset), width="stretch")
with col2:
    st.subheader("Mean impact by event type")
    by_type = es.groupby("event_type")["impact_score"].mean().sort_values(ascending=False).reset_index()
    fig = go.Figure(go.Bar(x=by_type["event_type"], y=by_type["impact_score"], marker_color="#9270CA"))
    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=None,
        yaxis_title="Mean impact score",
    )
    st.plotly_chart(fig, width="stretch")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Majors vs alt/DeFi beta rotation")
    st.plotly_chart(asset_rotation_chart(feats), width="stretch")
with col2:
    st.subheader("Cross-asset participation")
    st.plotly_chart(market_breadth_chart(feats), width="stretch")

st.subheader("Regime-conditional return distribution")
if not regime_cond.empty:
    fig = go.Figure()
    for asset, d in regime_cond.groupby("asset"):
        fig.add_trace(go.Bar(x=d["regime"], y=d["annualized_return"], name=asset))
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        title="Annualized return by regime (per asset)",
        xaxis_title=None,
        yaxis_title="Annualized return",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(regime_cond.round(4), width="stretch")

st.subheader("Top 10 unusual recent days (volume spike + abnormal on-chain or |return|>5%)")
recent = feats[feats["date"] >= feats["date"].max() - pd.Timedelta(days=180)]
unusual = recent[
    (recent["volume_spike_flag"] == 1)
    | (recent["abnormal_onchain_activity_flag"] == 1)
    | (recent["daily_return"].abs() > 0.05)
].sort_values("daily_return", key=lambda s: s.abs(), ascending=False).head(10)
if not unusual.empty:
    cols = ["date", "asset", "regime", "daily_return", "rolling_30d_volatility",
            "volatility_regime", "sentiment_score", "liquidity_stress_score",
            "market_breadth_positive_7d", "onchain_activity_index"]
    show_cols = [c for c in cols if c in unusual.columns]
    unusual_display = unusual[show_cols].copy()
    numeric_cols = unusual_display.select_dtypes(include="number").columns
    unusual_display[numeric_cols] = unusual_display[numeric_cols].round(4)
    st.dataframe(unusual_display, width="stretch")

render_analyst_takeaway(*strategy_takeaway(es, regime_cond, feats))
