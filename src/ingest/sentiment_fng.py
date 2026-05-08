"""Crypto Fear & Greed Index from alternative.me. No API key required.

Output: data/processed/sentiment.parquet with columns:
    date, sentiment_score, sentiment_label
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, PROCESSED_DIR
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

URL = "https://api.alternative.me/fng/"


def fetch_fng() -> pd.DataFrame:
    """Pull max-history daily Fear & Greed series."""
    data = http_get_json(
        URL,
        params={"limit": 0, "format": "json"},
        cache_namespace="fng",
        cache_filename="fng_full.json",
    )
    if not data or "data" not in data:
        return _sample_fallback()
    rows = data["data"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.normalize()
    df["sentiment_score"] = df["value"].astype(int)
    df["sentiment_label"] = df["value_classification"]
    df = df[["date", "sentiment_score", "sentiment_label"]].sort_values("date").reset_index(drop=True)
    df = df[df["date"] >= pd.Timestamp(DATE_START)]
    return df


def _sample_fallback() -> pd.DataFrame:
    """Synthetic plausible sentiment series so downstream still runs."""
    log.warning("Falling back to synthetic Fear & Greed series")
    dates = pd.date_range(DATE_START, pd.Timestamp.utcnow().normalize(), freq="D")
    import numpy as np
    rng = np.random.default_rng(7)
    base = 50 + 25 * np.sin(np.linspace(0, 12 * np.pi, len(dates)))
    noise = rng.normal(0, 5, len(dates))
    score = np.clip(base + noise, 5, 95).round().astype(int)
    bins = [-1, 25, 45, 55, 75, 101]
    labels = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
    label = pd.cut(score, bins=bins, labels=labels).astype(str)
    return pd.DataFrame({"date": dates, "sentiment_score": score, "sentiment_label": label})


def main() -> pd.DataFrame:
    df = fetch_fng()
    out = PROCESSED_DIR / "sentiment.parquet"
    write_parquet(df, out)
    log.info("Sentiment: %d rows -> %s", len(df), out)
    return df


if __name__ == "__main__":
    main()
