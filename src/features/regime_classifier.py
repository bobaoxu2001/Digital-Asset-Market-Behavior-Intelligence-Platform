"""Rule-based market behavior regime classifier.

Labels (precedence highest -> lowest):
    1. Event-driven
    2. Liquidity Stress
    3. Risk-off
    4. On-chain Activity Spike
    5. Momentum
    6. Calm
    7. Neutral

Inputs (per row): a wide feature frame keyed by (date, asset). Columns expected:
    rolling_30d_return, rolling_7d_return, rolling_30d_volatility,
    drawdown, sentiment_score, liquidity_stress_score, onchain_activity_index,
    volume_spike_flag, event_flag (all may contain NaN).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import REGIME_PARAMS


def _safe(val, default=np.nan):
    return default if pd.isna(val) else val


def classify_row(row: pd.Series, vol_low: float) -> str:
    """Apply precedence-ordered rules to a single feature row."""
    p = REGIME_PARAMS

    event_flag = _safe(row.get("event_flag", 0), 0)
    days_to = _safe(row.get("days_to_next_event", 999), 999)
    days_since = _safe(row.get("days_since_event", 999), 999)
    near_event = (event_flag == 1) or (days_to <= p["event_window_days"]) or (days_since <= p["event_window_days"])

    ret30 = _safe(row.get("rolling_30d_return"), 0)
    ret7 = _safe(row.get("rolling_7d_return"), 0)
    vol30 = _safe(row.get("rolling_30d_volatility"), 0)
    vol7 = _safe(row.get("rolling_7d_volatility"), 0)
    drawdown = _safe(row.get("drawdown"), 0)
    sent = _safe(row.get("sentiment_score"), 50)
    liq_stress = _safe(row.get("liquidity_stress_score"), 0)
    onchain = _safe(row.get("onchain_activity_index"), 0)
    vol_spike = _safe(row.get("volume_spike_flag", 0), 0)
    vol_z = _safe(row.get("volume_zscore_30d"), 0)
    tvl_7d = _safe(row.get("tvl_7d_change_pct"), 0)

    # 1. Event-driven: within event window AND elevated activity
    if near_event and (vol7 > 1.5 * vol30 if vol30 else False or abs(ret7) > 0.07):
        return "Event-driven"
    if near_event and abs(ret7) > 0.05:
        return "Event-driven"

    # 2. Liquidity Stress
    if liq_stress > p["liquidity_stress_threshold"] or (tvl_7d < -0.05 and ret7 < 0):
        return "Liquidity Stress"

    # 3. Risk-off
    if (ret30 < p["ret30_riskoff_threshold"] or drawdown < p["drawdown_riskoff_threshold"]) and sent < p["sentiment_riskoff_threshold"]:
        return "Risk-off"

    # 4. On-chain Activity Spike
    if onchain > p["onchain_spike_threshold"] and vol_spike == 1:
        return "On-chain Activity Spike"

    # 5. Momentum
    if ret30 > p["ret30_momentum_threshold"] and sent > p["sentiment_momentum_threshold"] and vol_z > 1:
        return "Momentum"

    # 6. Calm
    if vol30 and vol30 <= vol_low and abs(ret7) < 0.05:
        return "Calm"

    return "Neutral"


def classify(features: pd.DataFrame) -> pd.DataFrame:
    """Add a `regime` column to the feature frame, computed per asset."""
    if features.empty:
        return features
    out = []
    for asset, g in features.groupby("asset", sort=False):
        g = g.sort_values("date").copy()
        # vol_low_quantile: per-asset terciles of trailing 30d vol over the full sample
        vol_series = g["rolling_30d_volatility"].dropna()
        if vol_series.empty:
            vol_low = float("nan")
        else:
            vol_low = float(vol_series.quantile(REGIME_PARAMS["vol_low_quantile"]))
        g["regime"] = g.apply(lambda r: classify_row(r, vol_low), axis=1)
        out.append(g)
    return pd.concat(out, ignore_index=True)
