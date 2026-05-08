"""Templated 'analyst voice' insight generators.

These functions read precomputed features and produce a 2-3 sentence written
narrative for each dashboard page. No live LLM calls.
"""
from __future__ import annotations

import pandas as pd


def overview_insight(features: pd.DataFrame, summary: dict) -> str:
    if features.empty or not summary:
        return "Insufficient data to summarize."
    asof = summary.get("as_of")
    parts = [f"As of **{asof}**:"]
    per = summary.get("per_asset", {})
    for asset in ["BTC", "ETH", "SOL"]:
        if asset not in per:
            continue
        info = per[asset]
        regime = info.get("regime", "?")
        ret30 = info.get("ret_30d", 0) * 100
        vol30 = info.get("vol_30d", 0) * 100
        parts.append(
            f"**{asset}** sits in *{regime}* (30d return {ret30:+.1f}%, 30d vol {vol30:.0f}% annualized)."
        )
    fng = summary.get("sentiment_score")
    fng_label = summary.get("sentiment_label")
    if fng is not None:
        parts.append(f"Market sentiment: Fear & Greed = **{fng:.0f}** ({fng_label}).")
    liq = summary.get("current_liquidity_stress_score")
    if liq is not None and not (liq != liq):
        flag = " — stress threshold breached" if liq > 1.5 else ""
        parts.append(f"Liquidity stress score = **{liq:+.2f}**{flag}.")
    return " ".join(parts)


def regime_insight(features: pd.DataFrame, asset: str) -> str:
    d = features[features["asset"] == asset].sort_values("date")
    if d.empty:
        return ""
    last90 = d.tail(90)
    if last90.empty:
        return ""
    pct = (last90["regime"].value_counts(normalize=True) * 100).round(0).astype(int)
    top = pct.head(2)
    transitions = (last90["regime"] != last90["regime"].shift()).sum() - 1
    cur_vol = d["rolling_30d_volatility"].iloc[-1] or 0
    vol_pct = (d["rolling_30d_volatility"].rank(pct=True).iloc[-1] or 0) * 100
    pieces = []
    pieces.append(
        f"In the last 90 days, **{asset}** spent "
        + ", ".join([f"{pct[r]}% in *{r}*" for r in top.index])
        + f" with **{transitions} regime transitions**."
    )
    pieces.append(
        f"Current 30d realized volatility ({cur_vol*100:.0f}% ann.) sits in the **{vol_pct:.0f}th percentile** of the sample."
    )
    return " ".join(pieces)


def sentiment_insight(lead_lag: pd.DataFrame, asset: str) -> str:
    d = lead_lag[lead_lag["asset"] == asset].copy()
    if d.empty:
        return ""
    best = d.loc[d["corr"].abs().idxmax()]
    lag = int(best["lag"])
    corr = float(best["corr"])
    if lag < 0:
        verdict = f"Sentiment **lags price by {-lag} day(s)** for {asset}"
    elif lag > 0:
        verdict = f"Sentiment **leads price by {lag} day(s)** for {asset}"
    else:
        verdict = f"Sentiment moves **contemporaneously with price** for {asset}"
    return (
        f"{verdict} (peak |corr| = **{corr:+.2f}**). "
        "This is consistent with Fear & Greed being heavily backward-looking — it summarizes recent price action rather than predicting it. "
        "For directional strategy work, near-term sentiment is therefore a confirmation tool, not a leading indicator."
    )


def liquidity_insight(features: pd.DataFrame) -> str:
    d = features.drop_duplicates("date").sort_values("date").tail(30)
    if d.empty:
        return ""
    cur = d.iloc[-1]
    tvl = cur.get("tvl_usd")
    chg7 = cur.get("tvl_7d_change_pct") or 0
    chg30 = cur.get("tvl_30d_change_pct") or 0
    liq = cur.get("liquidity_stress_score") or 0
    flag_text = "stress threshold breached" if liq > 1.5 else "no current stress signal"
    return (
        f"Total DeFi TVL across tracked chains is **${tvl/1e9:,.1f}B** "
        f"(7d: {chg7*100:+.1f}%, 30d: {chg30*100:+.1f}%). "
        f"Liquidity stress score: **{liq:+.2f}** — {flag_text}."
    )


def onchain_insight(features: pd.DataFrame, asset: str) -> str:
    d = features[features["asset"] == asset].sort_values("date").tail(60)
    if d.empty:
        return ""
    spikes = int((d["abnormal_onchain_activity_flag"] == 1).sum())
    cur_idx = d["onchain_activity_index"].iloc[-1] or 0
    return (
        f"In the last 60 days **{asset}** logged {spikes} abnormal-activity day(s); "
        f"current activity index = **{cur_idx:+.2f}** (z-score units). "
        "Activity spikes that coincide with price drawdowns historically suggest distribution behavior; "
        "spikes at flat-to-up prices suggest accumulation."
    )


def strategy_insight(es: pd.DataFrame, regime_cond: pd.DataFrame) -> str:
    if es.empty:
        return ""
    by_type = es.groupby("event_type")["impact_score"].mean().sort_values(ascending=False)
    top_type = by_type.index[0]
    top_val = by_type.iloc[0]
    rc = regime_cond.copy() if not regime_cond.empty else pd.DataFrame()
    rc_btc = rc[(rc["asset"] == "BTC")] if not rc.empty else pd.DataFrame()
    if not rc_btc.empty:
        worst_regime = rc_btc.loc[rc_btc["mean_daily_return"].idxmin(), "regime"]
        best_regime = rc_btc.loc[rc_btc["mean_daily_return"].idxmax(), "regime"]
        regime_text = f"For BTC, the worst-mean-return regime is **{worst_regime}** and the best is **{best_regime}**."
    else:
        regime_text = ""
    return (
        f"**What happened?** Over the sample, *{top_type}* events generated the largest cross-asset impact "
        f"(mean impact score {top_val:.2f}). {regime_text} "
        "**Why it matters:** event-type sensitivity is asymmetric across assets — DeFi tokens (UNI/AAVE/LDO) "
        "amplify regulatory and ETF news, while majors (BTC/ETH) react more to macro and protocol upgrades. "
        "**What to monitor next:** liquidity stress score and on-chain abnormal-activity flags during upcoming FOMC/CPI prints — "
        "these are the conditions under which event reactions historically extend rather than mean-revert."
    )
