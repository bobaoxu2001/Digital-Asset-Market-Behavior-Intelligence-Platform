"""DeFiLlama: chain-level TVL, protocol-level TVL, stablecoin supply. No key required.

Outputs:
    data/processed/defi_chain_tvl.parquet  -- date, chain, tvl_usd
    data/processed/defi_protocol_tvl.parquet -- date, protocol, tvl_usd  (best-effort)
    data/processed/stablecoins.parquet -- date, stable_total_usd  (best-effort)
"""
from __future__ import annotations

import pandas as pd

from src.config import DATE_START, DEFI_CHAINS, DEFI_PROTOCOLS, PROCESSED_DIR
from src.utils.cache import http_get_json
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)

BASE = "https://api.llama.fi"
STABLE_BASE = "https://stablecoins.llama.fi"


def fetch_chain_tvl(chain: str) -> pd.DataFrame:
    url = f"{BASE}/v2/historicalChainTvl/{chain}"
    data = http_get_json(url, cache_namespace="defillama", cache_filename=f"chain_{chain}.json")
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"].astype(int), unit="s").dt.normalize()
    df["chain"] = chain
    df = df.rename(columns={"tvl": "tvl_usd"})[["date", "chain", "tvl_usd"]]
    return df[df["date"] >= pd.Timestamp(DATE_START)]


def fetch_protocol_tvl(slug: str) -> pd.DataFrame:
    url = f"{BASE}/protocol/{slug}"
    data = http_get_json(url, cache_namespace="defillama", cache_filename=f"proto_{slug}.json")
    if not data:
        return pd.DataFrame()
    series = data.get("tvl") or []
    if not series:
        return pd.DataFrame()
    df = pd.DataFrame(series)
    df["date"] = pd.to_datetime(df["date"].astype(int), unit="s").dt.normalize()
    df["protocol"] = slug
    df = df.rename(columns={"totalLiquidityUSD": "tvl_usd"})[["date", "protocol", "tvl_usd"]]
    return df[df["date"] >= pd.Timestamp(DATE_START)]


def fetch_stablecoin_supply() -> pd.DataFrame:
    url = f"{STABLE_BASE}/stablecoincharts/all"
    data = http_get_json(url, cache_namespace="defillama", cache_filename="stables_all.json")
    if not data:
        return pd.DataFrame()
    rows = []
    for r in data:
        ts = int(r.get("date", 0))
        peg = r.get("totalCirculatingUSD") or {}
        # peg is a dict like {"peggedUSD": <value>}
        total = sum(v for v in peg.values() if isinstance(v, (int, float)))
        if ts and total:
            rows.append({"date": pd.to_datetime(ts, unit="s").normalize(), "stable_total_usd": float(total)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df["date"] >= pd.Timestamp(DATE_START)]


def main() -> dict:
    out = {}
    chain_frames = []
    for c in DEFI_CHAINS:
        df = fetch_chain_tvl(c)
        if not df.empty:
            chain_frames.append(df)
        else:
            log.warning("DeFiLlama chain TVL empty for %s", c)
    if chain_frames:
        chain_df = pd.concat(chain_frames, ignore_index=True).sort_values(["chain", "date"])
        path = PROCESSED_DIR / "defi_chain_tvl.parquet"
        write_parquet(chain_df, path)
        log.info("Chain TVL: %d rows -> %s", len(chain_df), path)
        out["chain_tvl"] = chain_df
    else:
        log.error("No chain TVL data fetched")

    proto_frames = []
    for p in DEFI_PROTOCOLS:
        df = fetch_protocol_tvl(p)
        if not df.empty:
            proto_frames.append(df)
    if proto_frames:
        proto_df = pd.concat(proto_frames, ignore_index=True).sort_values(["protocol", "date"])
        path = PROCESSED_DIR / "defi_protocol_tvl.parquet"
        write_parquet(proto_df, path)
        log.info("Protocol TVL: %d rows -> %s", len(proto_df), path)
        out["protocol_tvl"] = proto_df

    stables = fetch_stablecoin_supply()
    if not stables.empty:
        path = PROCESSED_DIR / "stablecoins.parquet"
        write_parquet(stables, path)
        log.info("Stablecoins: %d rows -> %s", len(stables), path)
        out["stablecoins"] = stables
    else:
        log.warning("Stablecoin supply unavailable")
    return out


if __name__ == "__main__":
    main()
