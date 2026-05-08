"""Market data ingestion.

Strategy:
    1. yfinance pulls full daily price history (>365d back) reliably without an API key.
    2. CoinGecko Demo API enriches the trailing ~365 days with market_cap and
       USD-trade volume (where the Demo plan permits). Demo accounts cannot
       query historical depth >365d, so CoinGecko is supplemental, not primary.
    3. If CoinGecko fails entirely, yfinance prices/volumes alone are used.

Output: data/processed/market.parquet with columns:
    date, asset, coin_id, price, market_cap, volume, source
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from src.config import (
    ALL_ASSETS,
    COINGECKO_API_KEY,
    CORE_ASSETS,
    DATE_END,
    DATE_START,
    PROCESSED_DIR,
)
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

CG_BASE = "https://api.coingecko.com/api/v3"


def _cg_params(extra: dict) -> dict:
    """Add demo-API key as query param (works reliably with the public Demo plan)."""
    p = dict(extra)
    if COINGECKO_API_KEY:
        p["x_cg_demo_api_key"] = COINGECKO_API_KEY
    return p


def _to_unix(d: str) -> int:
    return int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp())


def fetch_coingecko_recent(coin_id: str, days: int = 365) -> pd.DataFrame:
    """Fetch daily price/mcap/volume from CoinGecko market_chart for the trailing
    `days` days. Uses the Demo-permitted endpoint; returns empty on auth failure.
    """
    url = f"{CG_BASE}/coins/{coin_id}/market_chart"
    params = _cg_params({"vs_currency": "usd", "days": str(days), "interval": "daily"})
    data = http_get_json(
        url,
        params=params,
        cache_namespace="coingecko",
        cache_filename=f"{coin_id}_recent_{days}d.json",
    )
    if not data or "prices" not in data or not data["prices"]:
        return pd.DataFrame()
    prices = pd.DataFrame(data["prices"], columns=["ts", "price"])
    mcaps = pd.DataFrame(data.get("market_caps", []), columns=["ts", "market_cap"])
    vols = pd.DataFrame(data.get("total_volumes", []), columns=["ts", "volume"])
    df = prices.merge(mcaps, on="ts", how="left").merge(vols, on="ts", how="left")
    df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
    df = df.groupby("date", as_index=False).agg({"price": "last", "market_cap": "last", "volume": "last"})
    df["source"] = "coingecko"
    return df


def fetch_yfinance_history(ticker: str, start: str, end: Optional[str]) -> pd.DataFrame:
    """yfinance fallback for daily OHLCV."""
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance not installed")
        return pd.DataFrame()
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as e:
        log.warning("yfinance failed for %s: %s", ticker, e)
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    out = pd.DataFrame({
        "date": pd.to_datetime(df["Date"]).dt.normalize(),
        "price": df["Close"].astype(float),
        "market_cap": pd.NA,
        "volume": df["Volume"].astype(float),
    })
    out["source"] = "yfinance"
    return out


def fetch_asset(asset: dict) -> pd.DataFrame:
    """yfinance for full history; CoinGecko enriches market_cap on the trailing year."""
    yf_df = fetch_yfinance_history(asset["yf_ticker"], DATE_START, DATE_END)
    cg_df = fetch_coingecko_recent(asset["id"], days=365)

    if yf_df.empty and cg_df.empty:
        log.error("Both yfinance and CoinGecko failed for %s", asset["symbol"])
        return pd.DataFrame()

    if yf_df.empty:
        df = cg_df
    elif cg_df.empty:
        df = yf_df
    else:
        # yfinance for backbone (full history), CoinGecko market_cap merged in for recent year
        cg_min = cg_df[["date", "market_cap"]].rename(columns={"market_cap": "market_cap_cg"})
        df = yf_df.merge(cg_min, on="date", how="left")
        df["market_cap"] = df["market_cap_cg"].combine_first(df["market_cap"])
        df = df.drop(columns=["market_cap_cg"])
        df["source"] = "yfinance+coingecko"

    df["asset"] = asset["symbol"]
    df["coin_id"] = asset["id"]
    return df[["date", "asset", "coin_id", "price", "market_cap", "volume", "source"]]


def main() -> pd.DataFrame:
    frames = []
    for asset in ALL_ASSETS:
        log.info("Fetching market data for %s (%s)", asset["symbol"], asset["id"])
        df = fetch_asset(asset)
        if not df.empty:
            frames.append(df)
        else:
            log.warning("No data for %s; skipping", asset["symbol"])
    if not frames:
        log.error("No market data fetched at all")
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True).sort_values(["asset", "date"]).reset_index(drop=True)
    out_path = PROCESSED_DIR / "market.parquet"
    write_parquet(combined, out_path)
    log.info("Wrote %d rows for %d assets to %s", len(combined), combined["asset"].nunique(), out_path)
    # If we got fewer than the core 3 assets, log clearly
    core_syms = {a["symbol"] for a in CORE_ASSETS}
    fetched = set(combined["asset"].unique())
    missing_core = core_syms - fetched
    if missing_core:
        log.warning("Missing core assets: %s", missing_core)
    return combined


if __name__ == "__main__":
    main()
