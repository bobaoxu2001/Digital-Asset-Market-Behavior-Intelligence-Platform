"""Templated 'analyst voice' insight generators.

These functions read precomputed features and produce a 2-3 sentence written
narrative for each dashboard page. No live LLM calls.
"""
from __future__ import annotations

import pandas as pd


def _pct(x, default: str = "N/A") -> str:
    try:
        if pd.isna(x):
            return default
        return f"{float(x) * 100:+.1f}%"
    except Exception:
        return default


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


def overview_takeaway(features: pd.DataFrame, summary: dict) -> tuple[str, str, str]:
    if features.empty or not summary:
        return (
            "The platform did not find enough processed data for a market snapshot.",
            "A professional dashboard should fail clearly instead of filling blank charts with zeros.",
            "Run the full pipeline or bundled demo staging before discussing results.",
        )
    per = summary.get("per_asset", {})
    btc = per.get("BTC", {})
    breadth = summary.get("market_breadth_positive_7d")
    liq = summary.get("current_liquidity_stress_score")
    fng = summary.get("sentiment_score")
    what = (
        f"BTC is labeled {btc.get('regime', 'N/A')} with 30d return {_pct(btc.get('ret_30d'))}; "
        f"7d breadth is {_pct(breadth)} and Fear & Greed is {fng:.0f}." if fng is not None else
        f"BTC is labeled {btc.get('regime', 'N/A')} with 30d return {_pct(btc.get('ret_30d'))}."
    )
    why = (
        "The first screen ties price, drawdown, sentiment, liquidity, and participation together, "
        "which is closer to a crypto research workflow than a single-price chart."
    )
    monitor = (
        f"Watch whether breadth falls below 50% while liquidity stress rises toward +1.5; "
        f"current liquidity stress is {liq:+.2f}." if liq is not None and not pd.isna(liq) else
        "Watch breadth, liquidity stress, and BTC drawdown together instead of reading any one signal alone."
    )
    return what, why, monitor


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


def regime_takeaway(features: pd.DataFrame, asset: str) -> tuple[str, str, str]:
    d = features[features["asset"] == asset].sort_values("date")
    if d.empty:
        return ("No rows for the selected asset.", "The page needs asset-level history to classify regimes.", "Select another asset or rebuild data.")
    latest = d.iloc[-1]
    last90 = d.tail(90)
    top_regime = last90["regime"].value_counts().idxmax() if not last90.empty else "N/A"
    transitions = int((last90["regime"] != last90["regime"].shift()).sum() - 1) if len(last90) > 1 else 0
    vol_regime = latest.get("volatility_regime", "N/A")
    what = f"{asset} is in {latest.get('regime', 'N/A')}; the last 90 days were dominated by {top_regime} with {transitions} transitions."
    why = f"The volatility label is {vol_regime}, so the same return move should be interpreted differently than it would be in a low-volatility tape."
    monitor = "Watch for regime transitions that combine rising 7d volatility, widening drawdown, and falling breadth."
    return what, why, monitor


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


def sentiment_takeaway(features: pd.DataFrame, lead_lag: pd.DataFrame, asset: str) -> tuple[str, str, str]:
    d = lead_lag[lead_lag["asset"] == asset].copy()
    corr_text = "N/A"
    lag_text = "N/A"
    if not d.empty:
        best = d.loc[d["corr"].abs().idxmax()]
        lag_text = f"{int(best['lag'])}d"
        corr_text = f"{float(best['corr']):+.2f}"
    latest_corr = "N/A"
    if "sentiment_return_corr_30d" in features.columns:
        f = features[features["asset"] == asset].sort_values("date")
        s = f["sentiment_return_corr_30d"].dropna()
        if not s.empty:
            latest_corr = f"{s.iloc[-1]:+.2f}"
    what = f"Peak sample lead-lag correlation is {corr_text} at lag {lag_text}; latest rolling 30d sentiment-return correlation is {latest_corr}."
    why = "Fear & Greed behaves more like a confirmation layer than a clean forward signal, which is useful for regime interpretation but weak as standalone alpha."
    monitor = "Look for sentiment confirmation after sharp return moves, and be skeptical when sentiment diverges from liquidity and breadth."
    return what, why, monitor


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


def liquidity_takeaway(features: pd.DataFrame) -> tuple[str, str, str]:
    d = features.drop_duplicates("date").sort_values("date").tail(30)
    if d.empty:
        return ("Liquidity data is unavailable.", "DeFi participation cannot be assessed without TVL and stablecoin rows.", "Regenerate DeFiLlama inputs.")
    cur = d.iloc[-1]
    tvl = cur.get("tvl_usd")
    chg7 = cur.get("tvl_7d_change_pct")
    stable_chg = cur.get("stablecoin_7d_change_pct")
    liq = cur.get("liquidity_stress_score")
    what = f"Tracked DeFi TVL is ${tvl/1e9:,.1f}B with 7d TVL change {_pct(chg7)} and liquidity stress {liq:+.2f}."
    why = f"Stablecoin supply change ({_pct(stable_chg)}) helps separate risk-on capital formation from price-only TVL movement."
    monitor = "Watch stress above +1.5 together with TVL contraction and falling stablecoin supply; that is the risk-management setup."
    return what, why, monitor


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


def onchain_takeaway(features: pd.DataFrame, asset: str) -> tuple[str, str, str]:
    d = features[features["asset"] == asset].sort_values("date").tail(60)
    if d.empty:
        return ("No meaningful on-chain history is loaded for this asset.", "The dashboard avoids pretending proxy data is native wallet-flow data.", "Run the full pipeline or add a paid native on-chain source.")
    spikes = int((d["abnormal_onchain_activity_flag"] == 1).sum()) if "abnormal_onchain_activity_flag" in d else 0
    idx = d["onchain_activity_index"].dropna().iloc[-1] if d["onchain_activity_index"].notna().any() else None
    what = f"{asset} recorded {spikes} abnormal-activity day(s) in the last 60 days; latest activity index is {idx:+.2f}." if idx is not None else f"{asset} has limited activity-index coverage in this sample."
    why = "On-chain spikes become strategy-relevant when they line up with drawdown, volume spikes, or liquidity stress rather than appearing in isolation."
    monitor = "Track whether the next activity spike occurs during falling price (possible distribution) or rising/flat price (possible accumulation)."
    return what, why, monitor


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
        "**Why it matters:** event-type sensitivity is asymmetric across assets — DeFi beta names (UNI/AAVE/LDO) "
        "amplify regulatory and ETF news, while majors (BTC/ETH) react more to macro and protocol upgrades. "
        "**What to monitor next:** liquidity stress score and on-chain abnormal-activity flags during upcoming FOMC/CPI prints — "
        "these are the conditions under which event reactions historically extend rather than mean-revert."
    )


def strategy_takeaway(es: pd.DataFrame, regime_cond: pd.DataFrame, features: pd.DataFrame | None = None) -> tuple[str, str, str]:
    if es.empty:
        return ("Event-study output is unavailable.", "The strategy page depends on event reactions and regime-conditioned returns.", "Run `make analysis` after feature generation.")
    by_type = es.groupby("event_type")["impact_score"].mean().sort_values(ascending=False)
    top_type = by_type.index[0]
    top_val = by_type.iloc[0]
    basket_text = "Alt/DeFi beta should be compared against majors before using event results as a strategy lens."
    if features is not None and not features.empty:
        recent = features[features["date"] >= features["date"].max() - pd.Timedelta(days=30)]
        if not recent.empty:
            majors = recent[recent["asset"].isin(["BTC", "ETH", "SOL"])]["daily_return"].mean()
            defi = recent[recent["asset"].isin(["UNI", "AAVE", "LDO", "MKR", "CRV", "AVAX"])]["daily_return"].mean()
            if pd.notna(majors) and pd.notna(defi):
                basket_text = f"Recent average daily return: majors {majors*100:+.2f}% vs alt/DeFi basket {defi*100:+.2f}%."
    what = f"{top_type} events have the highest mean impact score ({top_val:.2f}) in this sample."
    why = f"{basket_text} Event sensitivity differs by asset class, so catalyst views need sizing and expression discipline."
    monitor = "Pair upcoming FOMC/CPI/ETF catalysts with liquidity stress, breadth, and on-chain flags to decide whether reactions are likely to extend."
    return what, why, monitor
