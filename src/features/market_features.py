"""Per-asset price/volume features. All rolling windows are TRAILING-only."""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Input must have columns: date, asset, price, volume. Returns enriched copy.

    Output adds:
        daily_return, log_return,
        rolling_7d_return, rolling_30d_return,
        rolling_7d_volatility, rolling_30d_volatility,
        volume_zscore_30d, volume_spike_flag,
        drawdown, max_drawdown_30d
    """
    df = df.sort_values(["asset", "date"]).copy()
    out = []
    for asset, g in df.groupby("asset", sort=False):
        g = g.copy()
        g["daily_return"] = g["price"].pct_change()
        g["log_return"] = np.log(g["price"] / g["price"].shift(1))

        g["rolling_7d_return"] = g["price"].pct_change(7)
        g["rolling_30d_return"] = g["price"].pct_change(30)

        g["rolling_7d_volatility"] = g["log_return"].rolling(7, min_periods=3).std() * np.sqrt(365)
        g["rolling_30d_volatility"] = g["log_return"].rolling(30, min_periods=10).std() * np.sqrt(365)

        vol_mean = g["volume"].rolling(30, min_periods=10).mean()
        vol_std = g["volume"].rolling(30, min_periods=10).std()
        g["volume_zscore_30d"] = (g["volume"] - vol_mean) / vol_std.replace(0, np.nan)
        g["volume_spike_flag"] = (g["volume_zscore_30d"] > 2).fillna(False).astype(int)

        cummax = g["price"].cummax()
        g["drawdown"] = g["price"] / cummax - 1.0
        g["max_drawdown_30d"] = g["drawdown"].rolling(30, min_periods=5).min()

        out.append(g)
    return pd.concat(out, ignore_index=True)
