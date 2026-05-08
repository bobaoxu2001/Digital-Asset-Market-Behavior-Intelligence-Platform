"""Generate static PNG previews of every dashboard page from processed parquet data.

These previews are rendered with Plotly + kaleido (no browser, no Streamlit
needed). They are intentionally close-but-not-identical to the live Streamlit
view — the goal is a recruiter-readable preview in the README. For pixel-perfect
screenshots of the actual Streamlit dashboard, see README's "Manual screenshots"
section.

Usage:
    python3.11 scripts/generate_screenshots.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.components.charts import (  # noqa: E402
    drawdown_chart,
    event_impact_bar,
    event_type_heatmap,
    indexed_price_chart,
    lead_lag_chart,
    liquidity_stress_chart,
    onchain_chart,
    regime_distribution,
    regime_timeline,
    sentiment_price_chart,
    tvl_chart,
    vol_chart,
)
from src.config import PROCESSED_DIR  # noqa: E402
from src.utils.io import read_json_safe, read_parquet_safe  # noqa: E402

OUT = ROOT / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 1600
HEIGHT = 900
TEMPLATE = "plotly_dark"


def _save(fig: go.Figure, name: str, height: int = HEIGHT) -> Path:
    fig.update_layout(template=TEMPLATE, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                      font=dict(color="#F4F6FA", size=14), margin=dict(l=40, r=40, t=80, b=40))
    path = OUT / name
    fig.write_image(str(path), width=WIDTH, height=height, scale=2)
    print(f"  -> {path.relative_to(ROOT)}")
    return path


def _stitch(top: go.Figure, bottom: go.Figure, title: str) -> go.Figure:
    """Build a 2-row composite preview by inlining traces & shapes from two figures."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12,
                        subplot_titles=(top.layout.title.text or "", bottom.layout.title.text or ""))
    for tr in top.data:
        fig.add_trace(tr, row=1, col=1)
    for tr in bottom.data:
        fig.add_trace(tr, row=2, col=1)
    fig.update_layout(title=title, height=HEIGHT, showlegend=True)
    return fig


def page1_executive_overview(feats, summary):
    print("Page 1: Executive Overview")
    assets = ["BTC", "ETH", "SOL"]
    sub = feats[feats["asset"].isin(assets)]
    top = indexed_price_chart(sub, assets)
    bottom = drawdown_chart(sub, assets)
    fig = _stitch(top, bottom, "Executive Overview — multi-asset price & drawdown")
    _save(fig, "executive_overview.png")


def page2_regime_volatility(feats):
    print("Page 2: Market Regime & Volatility")
    sub = feats[feats["asset"].isin(["BTC", "ETH", "SOL"])]
    top = regime_timeline(sub, "BTC")
    bottom = regime_distribution(sub, ["BTC", "ETH", "SOL"])
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.14,
                        subplot_titles=(top.layout.title.text, bottom.layout.title.text))
    for tr in top.data:
        fig.add_trace(tr, row=1, col=1)
    for tr in bottom.data:
        fig.add_trace(tr, row=2, col=1)
    if top.layout.shapes:
        # apply regime ribbons only to row1 by re-anchoring xref/yref
        new_shapes = []
        for s in top.layout.shapes:
            sd = dict(s.to_plotly_json())
            sd["xref"] = "x"
            sd["yref"] = "y domain"
            new_shapes.append(sd)
        fig.update_layout(shapes=new_shapes)
    fig.update_layout(title="Market Regime & Volatility — BTC regime ribbon + cross-asset distribution",
                      height=HEIGHT)
    _save(fig, "market_regime_volatility.png")


def page3_sentiment_event(feats, ll):
    print("Page 3: Sentiment & Event Reaction")
    top = sentiment_price_chart(feats, "BTC")
    bottom = lead_lag_chart(ll, "BTC")
    fig = _stitch(top, bottom, "Sentiment & Event Reaction — BTC price vs F&G + lead-lag CCF")
    # preserve dual-axis on the top subplot
    fig.update_layout(yaxis2=dict(title="F&G", overlaying="y", side="right", range=[0, 100]))
    _save(fig, "sentiment_event_reaction.png")


def page4_liquidity_defi(feats, chain_view):
    print("Page 4: Liquidity & DeFi Participation")
    if not chain_view.empty:
        top = tvl_chart(chain_view)
    else:
        top = go.Figure()
    bottom = liquidity_stress_chart(feats)
    fig = _stitch(top, bottom, "Liquidity & DeFi Participation — chain TVL stack + liquidity stress")
    _save(fig, "liquidity_defi_participation.png")


def page5_onchain(feats):
    print("Page 5: On-chain Activity")
    top = onchain_chart(feats, "BTC")
    eth_d = feats[feats["asset"] == "ETH"]
    bottom_fig = go.Figure()
    if not eth_d.empty:
        d = eth_d.sort_values("date")
        bottom_fig.add_trace(go.Scatter(x=d["date"], y=d["onchain_activity_index"],
                                        mode="lines", name="ETH on-chain activity (proxy)",
                                        line=dict(color="#6DC8EC")))
        bottom_fig.update_layout(title="ETH: on-chain activity (DeFiLlama-derived flux proxy)")
    fig = _stitch(top, bottom_fig, "On-chain Activity — BTC native + ETH proxy")
    _save(fig, "onchain_activity.png")


def page6_strategy(es, typeasset):
    print("Page 6: Strategy Insights")
    top = event_impact_bar(es, top_n=10)
    bottom = event_type_heatmap(typeasset)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=(top.layout.title.text, bottom.layout.title.text))
    for tr in top.data:
        fig.add_trace(tr, row=1, col=1)
    for tr in bottom.data:
        fig.add_trace(tr, row=2, col=1)
    fig.update_layout(title="Strategy Insights — top events + event-type x asset heatmap",
                      height=HEIGHT, yaxis=dict(autorange="reversed"))
    _save(fig, "strategy_insights.png")


def main():
    feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
    if feats.empty:
        print("ERROR: features.parquet missing. Run `make ingest && make features && make analysis` first.")
        sys.exit(1)
    summary = read_json_safe(PROCESSED_DIR / "behavior_summary.json") or {}
    chain_view = read_parquet_safe(PROCESSED_DIR / "chain_tvl_view.parquet")
    es = read_parquet_safe(PROCESSED_DIR / "event_study.parquet")
    typeasset = read_parquet_safe(PROCESSED_DIR / "event_study_typeasset.parquet")
    ll = read_parquet_safe(PROCESSED_DIR / "lead_lag.parquet")

    page1_executive_overview(feats, summary)
    page2_regime_volatility(feats)
    page3_sentiment_event(feats, ll)
    page4_liquidity_defi(feats, chain_view)
    page5_onchain(feats)
    page6_strategy(es, typeasset)
    print(f"\nAll screenshots written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
