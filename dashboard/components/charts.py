"""Reusable Plotly chart factories."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

REGIME_COLORS = {
    "Calm": "#5B8FF9",
    "Momentum": "#5AD8A6",
    "Risk-off": "#E8684A",
    "Liquidity Stress": "#F6BD16",
    "Event-driven": "#9270CA",
    "On-chain Activity Spike": "#6DC8EC",
    "Neutral": "#B6B6B6",
}


def indexed_price_chart(market: pd.DataFrame, assets: list[str]) -> go.Figure:
    """Multi-asset price chart, indexed to 100 at the first date."""
    fig = go.Figure()
    for a in assets:
        d = market[market["asset"] == a].sort_values("date")
        if d.empty:
            continue
        norm = d["price"] / d["price"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=d["date"], y=norm, mode="lines", name=a))
    fig.update_layout(
        title="Price indexed to 100",
        xaxis_title=None,
        yaxis_title="Index (start=100)",
        template="plotly_dark",
        height=360,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def market_breadth_chart(features: pd.DataFrame) -> go.Figure:
    """Cross-asset participation signal from the wide feature table."""
    if features.empty or "market_breadth_positive_7d" not in features.columns:
        return go.Figure()
    d = features.drop_duplicates("date").sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["date"],
        y=d["market_breadth_positive_7d"] * 100,
        mode="lines",
        name="% assets positive over 7d",
        line=dict(color="#5AD8A6", width=2),
    ))
    if "cross_asset_return_dispersion_30d" in d.columns:
        fig.add_trace(go.Scatter(
            x=d["date"],
            y=d["cross_asset_return_dispersion_30d"] * 100,
            mode="lines",
            name="30d return dispersion",
            yaxis="y2",
            line=dict(color="#F6BD16", width=1.6),
        ))
    fig.add_hline(y=50, line_dash="dot", line_color="#94A3B8")
    fig.update_layout(
        title="Market breadth and rotation stress",
        xaxis_title=None,
        yaxis=dict(title="% assets positive 7d", range=[0, 100]),
        yaxis2=dict(title="Dispersion %", overlaying="y", side="right"),
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def asset_rotation_chart(features: pd.DataFrame) -> go.Figure:
    """Equal-weight major assets vs alt/DeFi beta basket indexed to 100."""
    if features.empty:
        return go.Figure()
    df = features[["date", "asset", "daily_return"]].dropna().copy()
    if df.empty:
        return go.Figure()

    groups = {
        "Majors: BTC/ETH/SOL": ["BTC", "ETH", "SOL"],
        "Alt/DeFi beta basket": ["UNI", "AAVE", "LDO", "MKR", "CRV", "AVAX"],
    }
    fig = go.Figure()
    for label, members in groups.items():
        sub = df[df["asset"].isin(members)]
        if sub.empty:
            continue
        ew = sub.groupby("date", as_index=False)["daily_return"].mean().sort_values("date")
        ew["index"] = (1 + ew["daily_return"].fillna(0)).cumprod() * 100
        fig.add_trace(go.Scatter(x=ew["date"], y=ew["index"], mode="lines", name=label))
    fig.update_layout(
        title="Asset rotation: majors vs alt/DeFi beta basket",
        xaxis_title=None,
        yaxis_title="Equal-weight index (start=100)",
        template="plotly_dark",
        height=340,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def regime_timeline(features: pd.DataFrame, asset: str) -> go.Figure:
    """Color-coded regime ribbon over price (fast - batched shapes)."""
    d = features[features["asset"] == asset].sort_values("date").reset_index(drop=True)
    if d.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["price"], mode="lines", name="Price", line=dict(color="white", width=1.5)))
    regimes = d["regime"].fillna("Neutral")
    # Identify contiguous blocks vectorized
    block_id = (regimes != regimes.shift()).cumsum()
    blocks = d.groupby(block_id).agg(start=("date", "first"), end=("date", "last"), regime=("regime", "first")).reset_index(drop=True)
    shapes = []
    for _, b in blocks.iterrows():
        shapes.append(dict(
            type="rect", xref="x", yref="paper",
            x0=b["start"], x1=b["end"], y0=0, y1=1,
            fillcolor=REGIME_COLORS.get(b["regime"], "#888"),
            opacity=0.18, line=dict(width=0), layer="below",
        ))
    fig.update_layout(
        title=f"{asset}: regime timeline",
        template="plotly_dark", height=380, margin=dict(l=10, r=10, t=40, b=10),
        shapes=shapes,
    )
    return fig


def drawdown_chart(features: pd.DataFrame, assets: list[str]) -> go.Figure:
    fig = go.Figure()
    for a in assets:
        d = features[features["asset"] == a].sort_values("date")
        if d.empty:
            continue
        fig.add_trace(go.Scatter(x=d["date"], y=d["drawdown"] * 100, mode="lines", name=a))
    fig.update_layout(
        title="Drawdown (% off trailing high)",
        yaxis_title="Drawdown %", template="plotly_dark", height=320, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def vol_chart(features: pd.DataFrame, asset: str) -> go.Figure:
    d = features[features["asset"] == asset].sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_30d_volatility"], mode="lines", name="30d realized vol"))
    fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_7d_volatility"], mode="lines", name="7d realized vol"))
    if "rolling_30d_volatility_percentile_365d" in d.columns:
        fig.add_trace(go.Scatter(
            x=d["date"],
            y=d["rolling_30d_volatility_percentile_365d"],
            mode="lines",
            name="365d vol percentile",
            yaxis="y2",
            line=dict(color="#F6BD16", width=1.4, dash="dot"),
        ))
    fig.update_layout(
        title=f"{asset}: realized volatility and percentile",
        yaxis=dict(title="Annualized vol"),
        yaxis2=dict(title="Percentile", overlaying="y", side="right", range=[0, 1]),
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def regime_distribution(features: pd.DataFrame, assets: list[str]) -> go.Figure:
    sub = features[features["asset"].isin(assets)]
    counts = sub.groupby(["asset", "regime"]).size().reset_index(name="days")
    fig = go.Figure()
    regimes = [r for r in REGIME_COLORS if r in set(counts["regime"])]
    for regime in regimes:
        d = counts[counts["regime"] == regime]
        fig.add_trace(go.Bar(
            x=d["asset"],
            y=d["days"],
            name=regime,
            marker_color=REGIME_COLORS.get(regime, "#B6B6B6"),
        ))
    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        title="Regime distribution by asset",
        xaxis_title=None,
        yaxis_title="Days",
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def sentiment_price_chart(features: pd.DataFrame, asset: str) -> go.Figure:
    d = features[features["asset"] == asset].sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["price"], name="Price", yaxis="y1", line=dict(color="white")))
    fig.add_trace(go.Scatter(x=d["date"], y=d["sentiment_score"], name="Fear & Greed", yaxis="y2", line=dict(color="#5AD8A6")))
    fig.update_layout(
        title=f"{asset}: price vs Fear & Greed",
        yaxis=dict(title="Price"), yaxis2=dict(title="F&G", overlaying="y", side="right", range=[0, 100]),
        template="plotly_dark", height=380, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def sentiment_corr_chart(features: pd.DataFrame, asset: str) -> go.Figure:
    d = features[features["asset"] == asset].sort_values("date")
    fig = go.Figure()
    if "sentiment_return_corr_30d" in d.columns:
        fig.add_trace(go.Scatter(
            x=d["date"],
            y=d["sentiment_return_corr_30d"],
            mode="lines",
            name="30d corr(ΔF&G, return)",
            line=dict(color="#5AD8A6", width=2),
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8")
    fig.update_layout(
        title=f"{asset}: rolling sentiment-return correlation",
        xaxis_title=None,
        yaxis_title="30d correlation",
        yaxis=dict(range=[-1, 1]),
        template="plotly_dark",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def lead_lag_chart(ll: pd.DataFrame, asset: str) -> go.Figure:
    d = ll[ll["asset"] == asset].sort_values("lag")
    fig = go.Figure(go.Bar(x=d["lag"], y=d["corr"], marker_color=["#5AD8A6" if x >= 0 else "#E8684A" for x in d["corr"]]))
    fig.update_layout(
        title=f"{asset}: corr(sentiment_change_t, return_t+lag)  -- positive lag = sentiment leads",
        xaxis_title="lag (days)", yaxis_title="correlation", template="plotly_dark",
        height=320, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def tvl_chart(chain_view: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = ["#5B8FF9", "#5AD8A6", "#F6BD16", "#9270CA", "#6DC8EC", "#E8684A"]
    for i, (chain, d) in enumerate(chain_view.sort_values("date").groupby("chain")):
        fig.add_trace(go.Scatter(
            x=d["date"],
            y=d["tvl_usd"],
            mode="lines",
            name=chain,
            stackgroup="one",
            line=dict(width=0.5, color=colors[i % len(colors)]),
        ))
    fig.update_layout(template="plotly_dark", title="DeFi TVL by chain", xaxis_title=None, yaxis_title="TVL (USD)")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def liquidity_stress_chart(features: pd.DataFrame) -> go.Figure:
    d = features.drop_duplicates("date").sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["liquidity_stress_score"], mode="lines", name="Liquidity Stress Score"))
    fig.add_hrect(y0=1.5, y1=max(d["liquidity_stress_score"].max() or 2, 2), fillcolor="#E8684A", opacity=0.18, line_width=0)
    fig.update_layout(title="Liquidity stress score (>1.5 = stress)", template="plotly_dark", height=320, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def onchain_chart(features: pd.DataFrame, asset: str) -> go.Figure:
    d = features[features["asset"] == asset].sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["onchain_activity_index"], mode="lines", name="On-chain activity index"))
    spikes = d[d["abnormal_onchain_activity_flag"] == 1]
    if not spikes.empty:
        fig.add_trace(go.Scatter(
            x=spikes["date"], y=spikes["onchain_activity_index"], mode="markers",
            marker=dict(color="#E8684A", size=8), name="Abnormal activity",
        ))
    fig.update_layout(title=f"{asset}: on-chain activity index", template="plotly_dark", height=320, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def event_impact_bar(es: pd.DataFrame, top_n: int = 10) -> go.Figure:
    d = es.sort_values("impact_score", ascending=False).head(top_n).copy()
    d["label"] = d["event_name"].str.slice(0, 50) + " — " + d["asset"]
    fig = go.Figure(go.Bar(x=d["impact_score"], y=d["label"], orientation="h", marker_color="#9270CA"))
    fig.update_layout(title=f"Top {top_n} events by impact score (directional move + vol expansion)",
                      template="plotly_dark", height=420, margin=dict(l=10, r=10, t=40, b=10), yaxis=dict(autorange="reversed"))
    return fig


def event_type_heatmap(typeasset: pd.DataFrame) -> go.Figure:
    if typeasset.empty:
        return go.Figure()
    df = typeasset.set_index("event_type")
    fig = go.Figure(go.Heatmap(z=df.values, x=df.columns, y=df.index, colorscale="Blues"))
    fig.update_layout(title="Mean impact score by event-type x asset", template="plotly_dark",
                      height=420, margin=dict(l=10, r=10, t=40, b=10))
    return fig
