"""GDELT 2.0 daily article-volume proxy for crypto news. Best-effort, optional.

Uses the GDELT DOC 2.0 API in `timelinevolinfo` mode. If GDELT is unavailable or
returns nothing, we silently skip (no fake data). Output (when present):
    data/processed/news_gdelt.parquet -- date, news_volume
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, PROCESSED_DIR
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt() -> pd.DataFrame:
    end = pd.Timestamp.utcnow().strftime("%Y%m%d%H%M%S")
    start = pd.Timestamp(DATE_START).strftime("%Y%m%d%H%M%S")
    params = {
        "query": '(bitcoin OR ethereum OR crypto OR cryptocurrency)',
        "mode": "timelinevol",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
        "timezoom": "yes",
    }
    data = http_get_json(URL, params=params, cache_namespace="gdelt", cache_filename="crypto_volume.json")
    if not data or "timeline" not in data or not data["timeline"]:
        return pd.DataFrame()
    series = data["timeline"][0].get("data", [])
    if not series:
        return pd.DataFrame()
    df = pd.DataFrame(series)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%dT%H%M%SZ", errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"])
    df["news_volume"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.groupby("date", as_index=False)["news_volume"].mean()
    return df


def main() -> pd.DataFrame:
    df = fetch_gdelt()
    if df.empty:
        log.warning("GDELT unavailable; skipping (downstream uses curated events instead)")
        return df
    path = PROCESSED_DIR / "news_gdelt.parquet"
    write_parquet(df, path)
    log.info("GDELT news volume: %d rows -> %s", len(df), path)
    return df


if __name__ == "__main__":
    main()
