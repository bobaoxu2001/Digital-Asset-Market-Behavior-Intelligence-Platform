"""On-chain activity features.

Builds per-asset on-chain features by joining BTC and ETH on-chain parquets.
For non-BTC/ETH assets, on-chain columns are NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _z(series: pd.Series, w: int = 30) -> pd.Series:
    m = series.rolling(w, min_periods=10).mean()
    s = series.rolling(w, min_periods=10).std()
    return (series - m) / s.replace(0, np.nan)


def build_onchain_features(btc: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    """Combine BTC and ETH on-chain into a per-(date, asset) feature frame.

    Output columns:
        date, asset, tx_count, active_addresses, fee_proxy,
        tx_count_zscore_30d, active_address_zscore_30d,
        onchain_activity_index, abnormal_onchain_activity_flag
    """
    frames = []
    for asset_df in (btc, eth):
        if asset_df is None or asset_df.empty:
            continue
        d = asset_df.sort_values("date").copy()
        d["tx_count_zscore_30d"] = _z(pd.to_numeric(d["tx_count"], errors="coerce"))
        d["active_address_zscore_30d"] = _z(pd.to_numeric(d["active_addresses"], errors="coerce"))
        d["fee_proxy_zscore_30d"] = _z(pd.to_numeric(d["fee_proxy"], errors="coerce"))
        comps = [d["tx_count_zscore_30d"], d["active_address_zscore_30d"], d["fee_proxy_zscore_30d"]]
        d["onchain_activity_index"] = sum(c.fillna(0) for c in comps) / sum(c.notna().astype(int) for c in comps).replace(0, np.nan)
        d["abnormal_onchain_activity_flag"] = (d["onchain_activity_index"] > 1.5).fillna(False).astype(int)
        frames.append(d[[
            "date", "asset", "tx_count", "active_addresses", "fee_proxy",
            "tx_count_zscore_30d", "active_address_zscore_30d",
            "onchain_activity_index", "abnormal_onchain_activity_flag",
        ]])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
