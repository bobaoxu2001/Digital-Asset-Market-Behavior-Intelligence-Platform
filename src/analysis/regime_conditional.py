"""Regime-conditional return statistics for the strategy page.

Output: data/processed/regime_conditional.parquet with rows = (asset, regime).
"""
from __future__ import annotations

import pandas as pd

from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe, write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)


def main() -> pd.DataFrame:
    feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
    if feats.empty:
        return pd.DataFrame()
    g = feats.groupby(["asset", "regime"])["daily_return"]
    summary = g.agg(["count", "mean", "std", "min", "max"]).reset_index()
    summary = summary.rename(columns={
        "count": "n_days",
        "mean": "mean_daily_return",
        "std": "std_daily_return",
        "min": "min_daily_return",
        "max": "max_daily_return",
    })
    # Annualized stats
    summary["annualized_return"] = (1 + summary["mean_daily_return"]) ** 365 - 1
    summary["annualized_vol"] = summary["std_daily_return"] * (365 ** 0.5)
    out = PROCESSED_DIR / "regime_conditional.parquet"
    write_parquet(summary, out)
    log.info("Regime-conditional: %d rows -> %s", len(summary), out)
    return summary


if __name__ == "__main__":
    main()
