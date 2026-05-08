"""Liquidity / DeFi features.

Builds:
    - Aggregate TVL across configured chains.
    - 1d/7d/30d % changes.
    - Stablecoin supply 7d % change (if stablecoin parquet present).
    - liquidity_stress_score: composite z-score of (negated) TVL trend, stablecoin
      shrinkage, and volume contraction. Values >1.5 marked as a flag.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.io import read_parquet_safe


def build_liquidity_features(chain_tvl: pd.DataFrame, stables: pd.DataFrame | None) -> pd.DataFrame:
    if chain_tvl.empty:
        return pd.DataFrame(columns=[
            "date", "tvl_usd", "tvl_1d_change_pct", "tvl_7d_change_pct",
            "tvl_30d_change_pct", "stable_total_usd", "stablecoin_7d_change_pct",
            "liquidity_stress_score", "liquidity_stress_flag",
        ])

    daily = chain_tvl.groupby("date", as_index=False)["tvl_usd"].sum().sort_values("date")
    daily["tvl_1d_change_pct"] = daily["tvl_usd"].pct_change()
    daily["tvl_7d_change_pct"] = daily["tvl_usd"].pct_change(7)
    daily["tvl_30d_change_pct"] = daily["tvl_usd"].pct_change(30)

    if stables is not None and not stables.empty:
        stables = stables.sort_values("date").copy()
        stables["stablecoin_7d_change_pct"] = stables["stable_total_usd"].pct_change(7)
        daily = daily.merge(stables[["date", "stable_total_usd", "stablecoin_7d_change_pct"]], on="date", how="left")
    else:
        daily["stable_total_usd"] = np.nan
        daily["stablecoin_7d_change_pct"] = np.nan

    # Liquidity stress: composite of (-tvl_7d, -stable_7d). Z-scored over 90d.
    def _z(series: pd.Series, w: int = 90) -> pd.Series:
        m = series.rolling(w, min_periods=20).mean()
        s = series.rolling(w, min_periods=20).std()
        return (series - m) / s.replace(0, np.nan)

    z_tvl_neg = -_z(daily["tvl_7d_change_pct"])
    z_stable_neg = -_z(daily["stablecoin_7d_change_pct"]) if "stablecoin_7d_change_pct" in daily else 0
    components = [c for c in [z_tvl_neg, z_stable_neg] if isinstance(c, pd.Series)]
    daily["liquidity_stress_score"] = sum(components) / max(len(components), 1)
    daily["liquidity_stress_flag"] = (daily["liquidity_stress_score"] > 1.5).fillna(False).astype(int)

    return daily


def build_chain_breakdown(chain_tvl: pd.DataFrame) -> pd.DataFrame:
    """Per-chain TVL with 7d % change, useful for the dashboard."""
    if chain_tvl.empty:
        return chain_tvl
    df = chain_tvl.sort_values(["chain", "date"]).copy()
    df["tvl_7d_change_pct"] = df.groupby("chain")["tvl_usd"].pct_change(7)
    return df
