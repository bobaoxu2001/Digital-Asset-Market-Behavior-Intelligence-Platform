"""On-chain Activity page."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.banner import render_sample_mode_banner
from dashboard.components.charts import onchain_chart
from dashboard.components.insights import onchain_insight
from dashboard.components.kpis import fmt_int, fmt_pct, fmt_signed, kpi_row
from src.config import PROCESSED_DIR
from src.utils.demo_data import ensure_processed_data
from src.utils.io import read_parquet_safe

ensure_processed_data()

st.set_page_config(page_title="On-chain Activity", layout="wide")
render_sample_mode_banner()

st.title("On-chain Activity")
st.caption("BTC native activity (Blockchain.com Charts) + ETH proxy activity (DeFiLlama-derived flux). Abnormal-day flags overlaid on price.")

with st.expander("Methodology note — ETH activity is a proxy on the free-tier stack"):
    st.markdown(
        "BTC on-chain features are taken directly from Blockchain.com Charts (`n-transactions`, "
        "`n-unique-addresses`, `transaction-fees-usd`).\n\n"
        "ETH on-chain features rely on a **DeFiLlama Ethereum-chain TVL flux proxy** because the "
        "Etherscan free-tier `dailytx`, `dailyavggasprice`, and `dailynewaddress` endpoints require "
        "Pro access. Activity *direction* is informative; absolute units differ from native chain "
        "counters. A Pro Etherscan key would replace the proxy in `src/ingest/onchain_etherscan.py` "
        "without other code changes."
    )

feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
if feats.empty:
    st.error("Run the pipeline first.")
    st.stop()


# ---------------------------------------------------------------------------
# Detect whether on-chain coverage is meaningful for the focus asset.
# We require a non-trivial number of non-null rows in the activity index for
# the asset to render KPIs and charts. Otherwise we show a professional
# fallback panel and stop the page.
# ---------------------------------------------------------------------------
def _has_meaningful_onchain(df: pd.DataFrame, asset: str, min_rows: int = 30) -> bool:
    if df.empty:
        return False
    sub = df[df["asset"] == asset]
    if sub.empty:
        return False
    cols = ["onchain_activity_index", "tx_count"]
    available = [c for c in cols if c in sub.columns]
    if not available:
        return False
    non_null = sub[available].notna().any(axis=1).sum()
    return int(non_null) >= min_rows


btc_ok = _has_meaningful_onchain(feats, "BTC")
eth_ok = _has_meaningful_onchain(feats, "ETH")

if not btc_ok and not eth_ok:
    st.info(
        "On-chain activity is limited in the hosted demo because native ETH transaction "
        "statistics require paid or Pro-tier endpoints, and the bundled sample slice does "
        "not include enough native BTC on-chain coverage to render charts honestly. BTC on-chain "
        "data and ETH proxy data are available in the full local pipeline when source data is "
        "present. This page is intentionally kept blank in sample mode to avoid presenting "
        "misleading zero values."
    )
    st.markdown(
        "**How to reproduce the full on-chain view locally**\n\n"
        "```bash\n"
        "make ingest && make features && make analysis\n"
        "```\n\n"
        "The local pipeline pulls BTC on-chain data from the public Blockchain.com Charts API "
        "(no key required) and an ETH activity proxy from DeFiLlama. With a Pro Etherscan key, "
        "the proxy is replaced by native ETH transaction counters in "
        "`src/ingest/onchain_etherscan.py` without other code changes."
    )
    st.stop()


with st.sidebar:
    available_assets = [a for a, ok in [("BTC", btc_ok), ("ETH", eth_ok)] if ok]
    asset = st.selectbox("Asset", available_assets)

g = feats[feats["asset"] == asset].sort_values("date")
last60 = g.tail(60)


def _last_non_null(series):
    """Return the most recent non-null value in `series`, or None if all-null/empty."""
    if series is None or series.empty:
        return None
    s = series.dropna()
    return None if s.empty else s.iloc[-1]


# Spikes: a real integer count, safe to display as 0 if column is all-null.
if (not last60.empty) and ("abnormal_onchain_activity_flag" in last60.columns):
    spikes_val = int((last60["abnormal_onchain_activity_flag"] == 1).sum())
    spikes_text = str(spikes_val)
else:
    spikes_text = "N/A"

cur_idx = _last_non_null(g["onchain_activity_index"]) if "onchain_activity_index" in g.columns else None
cur_tx = _last_non_null(g["tx_count"]) if "tx_count" in g.columns else None
cur_aa = _last_non_null(g["active_addresses"]) if "active_addresses" in g.columns else None

# 7d change in activity index — derivable from the activity index alone, so it
# is available for every asset that passed `_has_meaningful_onchain`. Keeps the
# KPI row visually balanced when a column like ``active_addresses`` is missing
# from the bundled sample (e.g. ETH proxy slice).
def _pct_change_7d(series: pd.Series):
    s = series.dropna() if series is not None else None
    if s is None or len(s) < 8:
        return None
    last, prior = s.iloc[-1], s.iloc[-8]
    if prior == 0 or pd.isna(prior):
        return None
    return float((last - prior) / abs(prior))

idx_7d = _pct_change_7d(g["onchain_activity_index"]) if "onchain_activity_index" in g.columns else None

candidate_items = [
    ("Activity index", fmt_signed(cur_idx)),
    ("Activity 7d change", fmt_pct(idx_7d)),
    ("Abnormal-activity days (60d)", spikes_text),
    ("Latest tx count", fmt_int(cur_tx)),
    ("Latest active addresses", fmt_int(cur_aa)),
]
# Drop any KPI that resolved to N/A so the row never shows placeholder cells.
items = [(label, value) for label, value in candidate_items if value != "N/A"]
if items:
    kpi_row(items)

st.plotly_chart(onchain_chart(feats, asset), use_container_width=True)

# Tx count + price overlay
if not g.empty and g["tx_count"].notna().any():
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
        "Note: ETH on-chain proxies are derived from DeFiLlama Ethereum-chain TVL flux because the "
        "Etherscan free-tier stats endpoints (`dailytx`, `dailygasused`) require Pro access. The "
        "activity direction is informative; absolute units differ from native chain counters."
    )

st.info(onchain_insight(feats, asset))
