"""Lead-lag analysis: cross-correlation between sentiment change and asset returns.

For each asset and lag k in [-7, +7], compute corr(sentiment_change(t), return(t+k)).
A POSITIVE k means sentiment leads return; NEGATIVE k means sentiment lags return.
Output: data/processed/lead_lag.parquet with columns (asset, lag, corr, n).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe, write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)


def cross_corr(sent_change: pd.Series, ret: pd.Series, lag: int) -> tuple[float, int]:
    """Lag>0: sentiment leads return; correlate sent(t) with ret(t+lag)."""
    if lag >= 0:
        s = sent_change.iloc[: len(sent_change) - lag]
        r = ret.iloc[lag:]
    else:
        s = sent_change.iloc[-lag:]
        r = ret.iloc[: len(ret) + lag]
    s = s.reset_index(drop=True)
    r = r.reset_index(drop=True)
    df = pd.DataFrame({"s": s, "r": r}).dropna()
    if len(df) < 30:
        return np.nan, len(df)
    return float(df["s"].corr(df["r"])), len(df)


def main() -> pd.DataFrame:
    feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
    if feats.empty:
        log.error("Features missing")
        return pd.DataFrame()
    rows = []
    for asset, g in feats.groupby("asset"):
        g = g.sort_values("date")
        sent_change = g["sentiment_score"].diff()
        ret = g["daily_return"]
        for lag in range(-7, 8):
            c, n = cross_corr(sent_change, ret, lag)
            rows.append({"asset": asset, "lag": lag, "corr": c, "n": n})
    df = pd.DataFrame(rows)
    out = PROCESSED_DIR / "lead_lag.parquet"
    write_parquet(df, out)
    log.info("Lead-lag: %d rows -> %s", len(df), out)
    return df


if __name__ == "__main__":
    main()
