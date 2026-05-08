"""On-chain Activity page."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import onchain_chart
from dashboard.components.insights import onchain_insight
from dashboard.components.kpis import kpi_row
from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe

st.set_page_config(page_title="On-chain Activity", layout="wide")
st.title("On-chain Activity")
st.caption("BTC native activity (Blockchain.com Charts) + ETH proxy activity (DeFiLlama-derived flux). Abnormal-day flags overlaid on price.")

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
if feats.empty:
    st.error("Run the pipeline first.")
    st.stop()

with st.sidebar:
    asset = st.selectbox("Asset (BTC and ETH have on-chain data)", ["BTC", "ETH"])

g = feats[feats["asset"] == asset].sort_values("date")
last60 = g.tail(60)
spikes = int((last60["abnormal_onchain_activity_flag"] == 1).sum()) if not last60.empty else 0
cur_idx = (g["onchain_activity_index"].iloc[-1] if not g.empty else 0) or 0
cur_tx = (g["tx_count"].iloc[-1] if not g.empty else 0)
cur_aa = (g["active_addresses"].iloc[-1] if not g.empty else 0)

items = [
    ("Activity index", f"{cur_idx:+.2f}"),
    ("Abnormal-activity days (60d)", str(spikes)),
    ("Latest tx count", f"{int(cur_tx):,}" if cur_tx and cur_tx == cur_tx else "—"),
    ("Latest active addresses", f"{int(cur_aa):,}" if cur_aa and cur_aa == cur_aa else "—"),
]
kpi_row(items)

st.plotly_chart(onchain_chart(feats, asset), use_container_width=True)

# Tx count + price overlay
if not g.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["date"], y=g["tx_count"], mode="lines", name="Tx count", yaxis="y1", line=dict(color="#6DC8EC")))
    fig.add_trace(go.Scatter(x=g["date"], y=g["price"], mode="lines", name="Price", yaxis="y2", line=dict(color="white")))
    fig.update_layout(
        template="plotly_dark", height=380,
        title=f"{asset}: tx count vs price",
        yaxis=dict(title="Tx count"),
        yaxis2=dict(title="Price", overlaying="y", side="right"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

# Abnormal markers on price
if not g.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["date"], y=g["price"], mode="lines", name="Price", line=dict(color="white")))
    spikes_df = g[g["abnormal_onchain_activity_flag"] == 1]
    if not spikes_df.empty:
        fig.add_trace(go.Scatter(
            x=spikes_df["date"], y=spikes_df["price"], mode="markers",
            marker=dict(size=8, color="#E8684A"), name="Abnormal activity",
        ))
    fig.update_layout(template="plotly_dark", height=320, title=f"{asset}: abnormal-activity flags overlaid on price",
                      margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ETH-specific note about Etherscan free tier limitation
if asset == "ETH":
    st.caption(
        "ℹ️ ETH on-chain proxies are derived from DeFiLlama Ethereum-chain TVL flux because Etherscan "
        "stats endpoints (`dailytx`, `dailygasused`) require Pro tier. The activity *direction* is "
        "informative; absolute units differ from native chain counters."
    )

st.info(onchain_insight(feats, asset))
