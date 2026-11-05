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
        g["rolling_30d_volatility_percentile_365d"] = (
            g["rolling_30d_volatility"]
            .rolling(365, min_periods=30)
            .apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        )
        g["volatility_regime"] = pd.cut(
            g["rolling_30d_volatility_percentile_365d"],
            bins=[-np.inf, 0.33, 0.67, np.inf],
            labels=["Low volatility", "Normal volatility", "High volatility"],
        ).astype("string").fillna("Insufficient history")

        vol_mean = g["volume"].rolling(30, min_periods=10).mean()
        vol_std = g["volume"].rolling(30, min_periods=10).std()
        g["volume_zscore_30d"] = (g["volume"] - vol_mean) / vol_std.replace(0, np.nan)
        g["volume_spike_flag"] = (g["volume_zscore_30d"] > 2).fillna(False).astype(int)

        cummax = g["price"].cummax()
        g["drawdown"] = g["price"] / cummax - 1.0
        g["max_drawdown_30d"] = g["drawdown"].rolling(30, min_periods=5).min()
        rolling_30d_low = g["price"].rolling(30, min_periods=5).min()
        g["rebound_from_30d_low"] = g["price"] / rolling_30d_low - 1.0

        out.append(g)
    return pd.concat(out, ignore_index=True)


def add_cross_asset_features(df: pd.DataFrame) -> pd.DataFrame:
    """Attach daily market breadth and dispersion signals to every asset row."""
    if df.empty:
        return df
    out = df.copy()

    def _positive_share(s: pd.Series) -> float:
        valid = s.dropna()
        if valid.empty:
            return float("nan")
        return float((valid > 0).mean())

    breadth = (
        out.groupby("date")
        .agg(
            market_breadth_positive_1d=("daily_return", _positive_share),
            market_breadth_positive_7d=("rolling_7d_return", _positive_share),
            cross_asset_return_dispersion_30d=("rolling_30d_return", "std"),
        )
        .reset_index()
    )
    return out.merge(breadth, on="date", how="left")


def add_sentiment_return_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling 30d correlation between daily Fear & Greed change and asset return."""
    if df.empty or "sentiment_score" not in df.columns:
        return df
    out = []
    for _, g in df.groupby("asset", sort=False):
        g = g.sort_values("date").copy()
        sentiment_change = pd.to_numeric(g["sentiment_score"], errors="coerce").diff()
        returns = pd.to_numeric(g["daily_return"], errors="coerce")
        g["sentiment_return_corr_30d"] = sentiment_change.rolling(30, min_periods=15).corr(returns)
        out.append(g)
    return pd.concat(out, ignore_index=True)
