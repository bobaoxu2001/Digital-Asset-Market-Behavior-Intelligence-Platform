"""ETH on-chain proxies via Etherscan free API.

We rely on two Etherscan stats endpoints:
    - dailytx (account=stats, action=dailytx)
    - dailygasused (action=dailygasused) and dailyavggasprice (action=dailyavggasprice)

The Etherscan free tier rate-limits and may reject historical bulk pulls without
a Pro subscription on some endpoints. If endpoints fail, we fall back to a
chain-level proxy derived from DeFiLlama Ethereum TVL daily change as an
"activity" proxy and document the limitation.

Output: data/processed/onchain_eth.parquet with columns:
    date, asset, tx_count, active_addresses, fee_proxy
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, ETHERSCAN_API_KEY, PROCESSED_DIR
from src.utils.cache import http_get_json
from src.utils.io import read_parquet_safe, write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

BASE = "https://api.etherscan.io/api"


def _fetch_etherscan_daily(action: str, value_field: str) -> pd.DataFrame:
    if not ETHERSCAN_API_KEY:
        log.warning("No ETHERSCAN_API_KEY; skipping action=%s", action)
        return pd.DataFrame()
    end_unix = int(pd.Timestamp.utcnow().timestamp())
    start_unix = int(pd.Timestamp(DATE_START).timestamp())
    params = {
        "module": "stats",
        "action": action,
        "startdate": pd.Timestamp(DATE_START).date().isoformat(),
        "enddate": pd.Timestamp.utcnow().date().isoformat(),
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY,
    }
    data = http_get_json(BASE, params=params, cache_namespace="etherscan", cache_filename=f"{action}.json")
    if not data or data.get("status") != "1" or not isinstance(data.get("result"), list):
        log.warning("Etherscan action=%s returned no usable result (msg=%s)", action, (data or {}).get("message"))
        return pd.DataFrame()
    rows = data["result"]
    df = pd.DataFrame(rows)
    if df.empty or "UTCDate" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["UTCDate"]).dt.normalize()
    if value_field not in df.columns:
        # Sometimes the value column is named differently
        cands = [c for c in df.columns if c.lower() == value_field.lower()]
        if cands:
            value_field = cands[0]
        else:
            return pd.DataFrame()
    df["value"] = pd.to_numeric(df[value_field], errors="coerce")
    return df[["date", "value"]].dropna()


def _eth_proxy_from_chain_tvl() -> pd.DataFrame:
    """Use Ethereum chain TVL daily volatility as a coarse 'activity' proxy when
    Etherscan endpoints are unavailable. Documented in README/memo as a known
    free-tier substitute, not a true tx-count number.
    """
    chain = read_parquet_safe(PROCESSED_DIR / "defi_chain_tvl.parquet")
    if chain.empty:
        return pd.DataFrame()
    eth = chain[chain["chain"] == "Ethereum"].copy()
    if eth.empty:
        return pd.DataFrame()
    eth = eth.sort_values("date").reset_index(drop=True)
    eth["fee_proxy"] = eth["tvl_usd"].pct_change().abs()  # daily TVL volatility ~= activity
    eth["tx_count"] = eth["tvl_usd"].diff().abs()  # absolute USD flux
    eth["active_addresses"] = pd.NA
    eth = eth.rename(columns={})[["date", "tx_count", "active_addresses", "fee_proxy"]]
    eth["asset"] = "ETH"
    return eth[["date", "asset", "tx_count", "active_addresses", "fee_proxy"]]


def main() -> pd.DataFrame:
    tx = _fetch_etherscan_daily("dailytx", "transactionCount")
    gasprice = _fetch_etherscan_daily("dailyavggasprice", "avgGasPrice_Wei")
    addresses = _fetch_etherscan_daily("dailynewaddress", "newAddressCount")

    frames = []
    if not tx.empty:
        frames.append(tx.rename(columns={"value": "tx_count"}))
    if not addresses.empty:
        frames.append(addresses.rename(columns={"value": "active_addresses"}))
    if not gasprice.empty:
        # convert Wei -> Gwei for readability
        gasprice["value"] = gasprice["value"] / 1e9
        frames.append(gasprice.rename(columns={"value": "fee_proxy"}))

    if not frames:
        log.warning("Etherscan returned nothing usable; using DeFiLlama ETH-TVL activity proxy")
        df = _eth_proxy_from_chain_tvl()
    else:
        df = frames[0]
        for f in frames[1:]:
            df = df.merge(f, on="date", how="outer")
        df["asset"] = "ETH"
        for c in ("tx_count", "active_addresses", "fee_proxy"):
            if c not in df.columns:
                df[c] = pd.NA
        df = df[["date", "asset", "tx_count", "active_addresses", "fee_proxy"]]

    if df is None or df.empty:
        log.error("No ETH on-chain data available from any source")
        return pd.DataFrame()

    df = df.sort_values("date").reset_index(drop=True)
    path = PROCESSED_DIR / "onchain_eth.parquet"
    write_parquet(df, path)
    log.info("ETH on-chain: %d rows -> %s", len(df), path)
    return df


if __name__ == "__main__":
    main()
