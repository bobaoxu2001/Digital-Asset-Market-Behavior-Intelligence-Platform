"""Macro context from FRED with yfinance fallback.

Output: data/processed/macro.parquet with columns:
    date, vix, treasury_10y, dxy_proxy, sp500
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, FRED_API_KEY, FRED_SERIES, PROCESSED_DIR, YF_MACRO
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_series(series_id: str) -> pd.DataFrame:
    if not FRED_API_KEY:
        return pd.DataFrame()
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": DATE_START,
    }
    data = http_get_json(FRED_URL, params=params, cache_namespace="fred", cache_filename=f"{series_id}.json")
    if not data or "observations" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["observations"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "value"]].dropna()


def fetch_yf_series(ticker: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()
    try:
        df = yf.download(ticker, start=DATE_START, progress=False, auto_adjust=True, threads=False)
    except Exception as e:
        log.warning("yfinance failed for %s: %s", ticker, e)
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return pd.DataFrame({"date": pd.to_datetime(df["Date"]).dt.normalize(), "value": df["Close"].astype(float)})


def main() -> pd.DataFrame:
    out = None
    yf_map = {v: k for k, v in YF_MACRO.items()}  # column_name -> yf_ticker
    for series_id, col in FRED_SERIES.items():
        df = fetch_fred_series(series_id)
        if df.empty:
            yf_ticker = yf_map.get(col)
            if yf_ticker:
                log.info("FRED %s empty; falling back to yfinance %s", series_id, yf_ticker)
                df = fetch_yf_series(yf_ticker)
        if df.empty:
            log.warning("Macro series %s/%s unavailable", series_id, col)
            continue
        df = df.rename(columns={"value": col})
        out = df if out is None else out.merge(df, on="date", how="outer")
    if out is None:
        log.error("No macro data fetched at all")
        return pd.DataFrame()
    out = out.sort_values("date").reset_index(drop=True)
    # Forward-fill macro series so weekend rows (which crypto has but equities don't) align
    for c in out.columns:
        if c != "date":
            out[c] = out[c].ffill()
    path = PROCESSED_DIR / "macro.parquet"
    write_parquet(out, path)
    log.info("Macro: %d rows -> %s", len(out), path)
    return out


if __name__ == "__main__":
    main()
