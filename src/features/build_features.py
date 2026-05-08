"""Master feature build: joins all sources into data/processed/features.parquet.

Schema (per row keyed by (date, asset)):
    market: price, market_cap, volume, daily_return, log_return,
            rolling_7d_return, rolling_30d_return, rolling_7d_volatility,
            rolling_30d_volatility, volume_zscore_30d, volume_spike_flag,
            drawdown, max_drawdown_30d
    sentiment: sentiment_score, sentiment_label, sentiment_3d_change,
            sentiment_7d_change, sentiment_zscore_30d, sentiment_regime
    liquidity: tvl_usd, tvl_1d_change_pct, tvl_7d_change_pct, tvl_30d_change_pct,
            stable_total_usd, stablecoin_7d_change_pct,
            liquidity_stress_score, liquidity_stress_flag
    onchain: tx_count, active_addresses, fee_proxy, tx_count_zscore_30d,
            active_address_zscore_30d, onchain_activity_index,
            abnormal_onchain_activity_flag
    macro: vix_level, vix_7d_change, treasury_10y, treasury_10y_7d_change,
            dxy_proxy, sp500, sp500_return_7d, crypto_macro_corr_30d
    events: event_flag, event_type, event_name, event_severity,
            days_since_event, days_to_next_event
    regime: regime
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.features.liquidity_features import build_chain_breakdown, build_liquidity_features
from src.features.macro_features import add_crypto_macro_corr, build_macro_features
from src.features.market_features import add_market_features
from src.features.onchain_features import build_onchain_features
from src.features.regime_classifier import classify
from src.features.sentiment_features import build_sentiment_features
from src.utils.io import read_parquet_safe, write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)


def _attach_event_features(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Add event_flag, event_type, event_name, event_severity, days_since/to."""
    if events.empty:
        df["event_flag"] = 0
        df["event_type"] = pd.NA
        df["event_name"] = pd.NA
        df["event_severity"] = 0
        df["days_since_event"] = 9999
        df["days_to_next_event"] = 9999
        return df

    ev = events.sort_values("date").copy()
    ev["date"] = pd.to_datetime(ev["date"]).dt.normalize()

    # event_flag/type/name/severity for exact-day matches; if multiple events same day
    # take highest severity
    daily_event = (
        ev.sort_values(["date", "severity"], ascending=[True, False])
        .drop_duplicates("date", keep="first")
    )
    df = df.merge(
        daily_event[["date", "event_type", "event_name", "severity"]].rename(columns={"severity": "event_severity"}),
        on="date",
        how="left",
    )
    df["event_flag"] = df["event_type"].notna().astype(int)
    df["event_severity"] = df["event_severity"].fillna(0).astype(int)

    # days_since / days_to (use sorted unique event dates)
    event_dates = ev["date"].drop_duplicates().sort_values().to_numpy()
    all_dates = df["date"].sort_values().to_numpy()

    def _days_since(d):
        prior = event_dates[event_dates <= d]
        if len(prior) == 0:
            return 9999
        return int((d - prior[-1]) / np.timedelta64(1, "D"))

    def _days_to(d):
        future = event_dates[event_dates >= d]
        if len(future) == 0:
            return 9999
        return int((future[0] - d) / np.timedelta64(1, "D"))

    unique_dates = pd.Series(all_dates).drop_duplicates()
    days_since = unique_dates.map(_days_since)
    days_to = unique_dates.map(_days_to)
    daymap = pd.DataFrame({"date": unique_dates.values, "days_since_event": days_since.values, "days_to_next_event": days_to.values})
    df = df.merge(daymap, on="date", how="left")
    return df


def main() -> pd.DataFrame:
    market = read_parquet_safe(PROCESSED_DIR / "market.parquet")
    sentiment = read_parquet_safe(PROCESSED_DIR / "sentiment.parquet")
    chain_tvl = read_parquet_safe(PROCESSED_DIR / "defi_chain_tvl.parquet")
    stables = read_parquet_safe(PROCESSED_DIR / "stablecoins.parquet")
    onchain_btc = read_parquet_safe(PROCESSED_DIR / "onchain_btc.parquet")
    onchain_eth = read_parquet_safe(PROCESSED_DIR / "onchain_eth.parquet")
    macro = read_parquet_safe(PROCESSED_DIR / "macro.parquet")
    events = read_parquet_safe(PROCESSED_DIR / "events.parquet")

    if market.empty:
        log.error("Cannot build features: market parquet missing or empty")
        return pd.DataFrame()

    log.info("Building market features ...")
    feats = add_market_features(market)

    log.info("Joining sentiment ...")
    sent_feats = build_sentiment_features(sentiment) if not sentiment.empty else pd.DataFrame()
    if not sent_feats.empty:
        feats = feats.merge(sent_feats, on="date", how="left")

    log.info("Joining liquidity ...")
    liq = build_liquidity_features(chain_tvl, stables)
    if not liq.empty:
        feats = feats.merge(liq, on="date", how="left")

    log.info("Joining on-chain ...")
    onchain_feats = build_onchain_features(onchain_btc, onchain_eth)
    if not onchain_feats.empty:
        feats = feats.merge(onchain_feats, on=["date", "asset"], how="left")

    log.info("Joining macro ...")
    macro_feats = build_macro_features(macro)
    if not macro_feats.empty:
        feats = feats.merge(macro_feats, on="date", how="left")
        # forward-fill macro features (equities don't trade weekends, crypto does)
        macro_cols = [c for c in macro_feats.columns if c != "date"]
        feats[macro_cols] = feats.groupby("asset")[macro_cols].ffill()
        cmc = add_crypto_macro_corr(market, macro, asset="BTC")
        if not cmc.empty:
            feats = feats.merge(cmc, on="date", how="left")
            feats["crypto_macro_corr_30d"] = feats.groupby("asset")["crypto_macro_corr_30d"].ffill()

    log.info("Attaching event features ...")
    feats = _attach_event_features(feats, events)

    log.info("Classifying regimes ...")
    feats = classify(feats)

    out_path = PROCESSED_DIR / "features.parquet"
    write_parquet(feats, out_path)
    log.info("features: %d rows, %d columns -> %s", len(feats), feats.shape[1], out_path)

    # Also write per-chain TVL breakdown for the dashboard
    chain_view = build_chain_breakdown(chain_tvl)
    if not chain_view.empty:
        write_parquet(chain_view, PROCESSED_DIR / "chain_tvl_view.parquet")

    return feats


if __name__ == "__main__":
    main()
