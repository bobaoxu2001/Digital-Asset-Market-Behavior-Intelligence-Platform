"""High-level behavior summary used by the dashboard's auto-generated insight panels.

Output: data/processed/behavior_summary.json with current snapshot fields.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe, write_json
from src.utils.logging import get_logger

log = get_logger(__name__)


def _latest(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    return df.sort_values("date").iloc[-1]


def main() -> dict:
    feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
    if feats.empty:
        log.error("No features for summary")
        return {}

    asof = pd.Timestamp(feats["date"].max()).date().isoformat()

    per_asset = {}
    for asset, g in feats.groupby("asset"):
        g = g.sort_values("date")
        latest = g.iloc[-1]
        per_asset[asset] = {
            "regime": str(latest.get("regime")),
            "price": float(latest.get("price", float("nan"))),
            "ret_30d": float(latest.get("rolling_30d_return") or 0),
            "vol_30d": float(latest.get("rolling_30d_volatility") or 0),
            "drawdown": float(latest.get("drawdown") or 0),
            "regime_pct_last_90d": (
                g.tail(90)["regime"].value_counts(normalize=True).round(3).to_dict()
            ),
        }

    sentiment_score = float(feats.sort_values("date").iloc[-1].get("sentiment_score") or float("nan"))
    sentiment_label = str(feats.sort_values("date").iloc[-1].get("sentiment_label"))
    tvl = float(feats.sort_values("date").iloc[-1].get("tvl_usd") or float("nan"))
    liq_score = float(feats.sort_values("date").iloc[-1].get("liquidity_stress_score") or float("nan"))

    summary = {
        "as_of": asof,
        "generated_at": datetime.utcnow().isoformat(),
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "current_tvl_usd": tvl,
        "current_liquidity_stress_score": liq_score,
        "per_asset": per_asset,
    }

    out = PROCESSED_DIR / "behavior_summary.json"
    write_json(summary, out)
    log.info("Behavior summary -> %s", out)
    return summary


if __name__ == "__main__":
    main()
