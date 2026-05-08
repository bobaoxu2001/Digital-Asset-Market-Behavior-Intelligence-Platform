"""Sentiment & Event Reaction page."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import lead_lag_chart, sentiment_price_chart
from dashboard.components.insights import sentiment_insight
from dashboard.components.kpis import fmt_pct, kpi_row
from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe

st.set_page_config(page_title="Sentiment & Event Reaction", layout="wide")
st.title("Sentiment & Event Reaction")
st.caption("Fear & Greed vs price, lead-lag CCF, curated-event overlay, and per-event reaction anatomy.")

with st.expander("Methodology note — how to read the lead-lag chart"):
    st.markdown(
        "The lead-lag chart shows the sample correlation between the daily change in the Fear & "
        "Greed Index and the asset's daily return shifted by `lag` days.\n\n"
        "- **Positive lag** would mean sentiment *leads* return (sentiment change at *t* correlates "
        "with return at *t+lag*).\n"
        "- **Negative lag** means sentiment *lags* return — sentiment is reacting to recent realized "
        "price action.\n\n"
        "Across all tracked assets the peak |correlation| occurs at **lag = −1**. This describes the "
        "Fear & Greed proxy, which is constructed to weight recent price action heavily; it is not "
        "predictive alpha and there is no look-ahead in the underlying features."
    )

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
events = read_parquet_safe(PROCESSED_DIR / "events.parquet")
ll = read_parquet_safe(PROCESSED_DIR / "lead_lag.parquet")
es = read_parquet_safe(PROCESSED_DIR / "event_study.parquet")

if feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

all_assets = sorted(feats["asset"].unique())
with st.sidebar:
    asset = st.selectbox("Asset", [a for a in ["BTC", "ETH", "SOL"] if a in all_assets] + [a for a in all_assets if a not in ("BTC", "ETH", "SOL")])
    event_types = ["(all)"] + (sorted(events["event_type"].dropna().unique().tolist()) if not events.empty else [])
    selected_type = st.selectbox("Event type", event_types)
    if not events.empty:
        evnames = events.sort_values("date", ascending=False)["event_name"].tolist()
        focus_event = st.selectbox("Focus event for anatomy chart", ["(none)"] + evnames)
    else:
        focus_event = "(none)"

cur_fng = feats.sort_values("date").iloc[-1]
items = [
    ("Fear & Greed", str(int(cur_fng.get("sentiment_score") or 0))),
    ("Sentiment label", str(cur_fng.get("sentiment_label", "—"))),
    ("7d sentiment shift", f"{(cur_fng.get('sentiment_7d_change') or 0):+.0f}"),
]
if not ll.empty:
    d = ll[ll["asset"] == asset]
    if not d.empty:
        best = d.loc[d["corr"].abs().idxmax()]
        items.append(("Sentiment lead/lag (best |r|)", f"lag {int(best['lag'])}d  r={best['corr']:+.2f}"))
kpi_row(items)

st.plotly_chart(sentiment_price_chart(feats, asset), use_container_width=True)

# Event markers overlaid on price
if not events.empty:
    df = feats[feats["asset"] == asset].sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["price"], mode="lines", name=f"{asset} Price", line=dict(color="white")))
    ev = events.copy()
    if selected_type != "(all)":
        ev = ev[ev["event_type"] == selected_type]
    # join price for marker y-coord
    ev = ev.merge(df[["date", "price"]], on="date", how="left").dropna(subset=["price"])
    if not ev.empty:
        fig.add_trace(go.Scatter(
            x=ev["date"], y=ev["price"], mode="markers",
            marker=dict(size=10, color="#F6BD16", line=dict(color="white", width=1)),
            text=ev["event_name"], hovertemplate="%{text}<br>%{x|%Y-%m-%d}<extra></extra>",
            name="Events",
        ))
    fig.update_layout(template="plotly_dark", height=380, title=f"{asset}: events overlay", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

# Selected event reaction "anatomy"
if focus_event != "(none)" and not es.empty:
    sub = es[(es["event_name"] == focus_event) & (es["asset"] == asset)]
    if not sub.empty:
        st.subheader(f"Event reaction: {focus_event}")
        row = sub.iloc[0]
        cols = st.columns(4)
        cols[0].metric("[-1, +1] return", fmt_pct(row["ret_pre1_post1"]))
        cols[1].metric("[t, +3] return", fmt_pct(row["ret_t_t3"]))
        cols[2].metric("[t, +7] return", fmt_pct(row["ret_t_t7"]))
        cols[3].metric("Vol ratio post/pre", f"{row['vol_ratio']:.2f}" if pd.notna(row["vol_ratio"]) else "—")

if not ll.empty:
    st.plotly_chart(lead_lag_chart(ll, asset), use_container_width=True)

st.info(sentiment_insight(ll, asset) if not ll.empty else "Lead-lag data unavailable.")
