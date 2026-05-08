"""BTC on-chain proxies via Blockchain.com Charts API. No key required.

Series collected:
    - n-transactions  (daily transaction count)
    - n-unique-addresses (active addresses, used as a proxy)
    - mempool-size (mempool bytes; gas/fee proxy for BTC)

Output: data/processed/onchain_btc.parquet with columns:
    date, asset, tx_count, active_addresses, fee_proxy
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, PROCESSED_DIR
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

BASE = "https://api.blockchain.info/charts"
SERIES = {
    "tx_count": "n-transactions",
    "active_addresses": "n-unique-addresses",
    "fee_proxy": "transaction-fees-usd",
}


def fetch_series(name: str) -> pd.DataFrame:
    url = f"{BASE}/{name}"
    params = {"timespan": "all", "format": "json", "sampled": "false"}
    data = http_get_json(url, params=params, cache_namespace="blockchain", cache_filename=f"{name}.json")
    if not data or "values" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["values"])
    df["date"] = pd.to_datetime(df["x"].astype(int), unit="s").dt.normalize()
    df = df.rename(columns={"y": "value"})[["date", "value"]]
    return df[df["date"] >= pd.Timestamp(DATE_START)]


def main() -> pd.DataFrame:
    out = None
    for col, slug in SERIES.items():
        df = fetch_series(slug)
        if df.empty:
            log.warning("Blockchain.com series %s empty", slug)
            continue
        df = df.rename(columns={"value": col})
        out = df if out is None else out.merge(df, on="date", how="outer")
    if out is None or out.empty:
        log.error("No BTC on-chain data; downstream features will be NaN")
        return pd.DataFrame()
    out = out.sort_values("date").reset_index(drop=True)
    out["asset"] = "BTC"
    cols = ["date", "asset"] + [c for c in ["tx_count", "active_addresses", "fee_proxy"] if c in out.columns]
    out = out[cols]
    path = PROCESSED_DIR / "onchain_btc.parquet"
    write_parquet(out, path)
    log.info("BTC on-chain: %d rows -> %s", len(out), path)
    return out


if __name__ == "__main__":
    main()
