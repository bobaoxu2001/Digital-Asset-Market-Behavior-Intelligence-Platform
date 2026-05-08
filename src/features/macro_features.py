"""Macro features."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_macro_features(macro: pd.DataFrame) -> pd.DataFrame:
    if macro.empty:
        return macro
    df = macro.sort_values("date").copy()
    if "vix" in df:
        df["vix_level"] = df["vix"]
        df["vix_7d_change"] = df["vix"].diff(7)
    if "treasury_10y" in df:
        df["treasury_10y_7d_change"] = df["treasury_10y"].diff(7)
    if "sp500" in df:
        df["sp500_return_7d"] = df["sp500"].pct_change(7)
    keep = ["date"] + [c for c in [
        "vix_level", "vix_7d_change", "treasury_10y", "treasury_10y_7d_change",
        "dxy_proxy", "sp500", "sp500_return_7d",
    ] if c in df.columns]
    return df[keep]


def add_crypto_macro_corr(market: pd.DataFrame, macro: pd.DataFrame, asset: str = "BTC") -> pd.DataFrame:
    """Rolling 30d correlation between asset daily return and S&P 500 daily return.

    Returns a date-indexed DataFrame with column `crypto_macro_corr_30d` to merge in.
    """
    if "sp500" not in macro.columns:
        return pd.DataFrame(columns=["date", "crypto_macro_corr_30d"])
    btc = market[market["asset"] == asset][["date", "price"]].sort_values("date").copy()
    btc["btc_ret"] = btc["price"].pct_change()
    sp = macro[["date", "sp500"]].sort_values("date").copy()
    sp["sp_ret"] = sp["sp500"].pct_change()
    df = btc.merge(sp[["date", "sp_ret"]], on="date", how="inner")
    df["crypto_macro_corr_30d"] = df["btc_ret"].rolling(30, min_periods=10).corr(df["sp_ret"])
    return df[["date", "crypto_macro_corr_30d"]]
