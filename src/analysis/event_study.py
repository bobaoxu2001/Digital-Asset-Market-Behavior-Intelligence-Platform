"""Event study: compute reaction metrics around each curated event for each asset.

Output: data/processed/event_study.parquet with rows = (event_date, asset).
Columns include:
    event_date, event_type, event_name, severity, asset,
    ret_pre1_post1, ret_t_t3, ret_t_t7,
    vol_pre, vol_post, vol_ratio,
    volume_pre_mean, volume_post_mean, volume_ratio,
    sentiment_pre, sentiment_post, sentiment_shift,
    tvl_pre, tvl_post, tvl_change_pct,
    onchain_pre, onchain_post, onchain_shift,
    impact_score   -- composite |ret_t_t7| z-scaled + |vol_ratio-1| z-scaled
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.utils.io import read_parquet_safe, write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)


def _window_slice(df: pd.DataFrame, event_date: pd.Timestamp, lo: int, hi: int) -> pd.DataFrame:
    mask = (df["date"] >= event_date + pd.Timedelta(days=lo)) & (df["date"] <= event_date + pd.Timedelta(days=hi))
    return df[mask]


def _ret_between(asset_df: pd.DataFrame, event_date: pd.Timestamp, lo: int, hi: int) -> float:
    """Cumulative log return from t+lo close to t+hi close."""
    sub = _window_slice(asset_df, event_date, lo, hi).sort_values("date")
    if len(sub) < 2:
        return np.nan
    return float(np.log(sub["price"].iloc[-1] / sub["price"].iloc[0]))


def study_event(event: pd.Series, asset_df: pd.DataFrame, sent: pd.DataFrame, liq: pd.DataFrame, onchain: pd.DataFrame) -> dict:
    ed = pd.to_datetime(event["date"]).normalize()
    asset = asset_df["asset"].iloc[0]

    pre = _window_slice(asset_df, ed, -5, -1)
    post = _window_slice(asset_df, ed, 1, 5)

    ret_pre1_post1 = _ret_between(asset_df, ed, -1, 1)
    ret_t_t3 = _ret_between(asset_df, ed, 0, 3)
    ret_t_t7 = _ret_between(asset_df, ed, 0, 7)

    vol_pre = pre["log_return"].std() * np.sqrt(365) if len(pre) > 1 else np.nan
    vol_post = post["log_return"].std() * np.sqrt(365) if len(post) > 1 else np.nan
    vol_ratio = (vol_post / vol_pre) if (vol_pre and not np.isnan(vol_pre) and vol_pre > 0) else np.nan

    volume_pre = pre["volume"].mean() if not pre.empty else np.nan
    volume_post = post["volume"].mean() if not post.empty else np.nan
    volume_ratio = (volume_post / volume_pre) if (volume_pre and volume_pre > 0) else np.nan

    sent_pre = sent_post = sent_shift = np.nan
    if not sent.empty:
        sp = sent[(sent["date"] >= ed - pd.Timedelta(days=5)) & (sent["date"] < ed)]["sentiment_score"].mean()
        spo = sent[(sent["date"] > ed) & (sent["date"] <= ed + pd.Timedelta(days=5))]["sentiment_score"].mean()
        sent_pre = float(sp) if not np.isnan(sp) else np.nan
        sent_post = float(spo) if not np.isnan(spo) else np.nan
        if not (np.isnan(sent_pre) or np.isnan(sent_post)):
            sent_shift = sent_post - sent_pre

    tvl_pre = tvl_post = tvl_change = np.nan
    if not liq.empty:
        l_pre = liq[(liq["date"] >= ed - pd.Timedelta(days=5)) & (liq["date"] < ed)]["tvl_usd"].mean()
        l_post = liq[(liq["date"] > ed) & (liq["date"] <= ed + pd.Timedelta(days=5))]["tvl_usd"].mean()
        tvl_pre = float(l_pre) if not np.isnan(l_pre) else np.nan
        tvl_post = float(l_post) if not np.isnan(l_post) else np.nan
        if tvl_pre and tvl_pre > 0 and not np.isnan(tvl_post):
            tvl_change = (tvl_post - tvl_pre) / tvl_pre

    onchain_pre = onchain_post = onchain_shift = np.nan
    if not onchain.empty:
        oc = onchain[onchain["asset"] == asset]
        if not oc.empty:
            o_pre = oc[(oc["date"] >= ed - pd.Timedelta(days=5)) & (oc["date"] < ed)]["onchain_activity_index"].mean()
            o_post = oc[(oc["date"] > ed) & (oc["date"] <= ed + pd.Timedelta(days=5))]["onchain_activity_index"].mean()
            onchain_pre = float(o_pre) if not np.isnan(o_pre) else np.nan
            onchain_post = float(o_post) if not np.isnan(o_post) else np.nan
            if not (np.isnan(onchain_pre) or np.isnan(onchain_post)):
                onchain_shift = onchain_post - onchain_pre

    return {
        "event_date": ed,
        "event_type": event["event_type"],
        "event_name": event["event_name"],
        "severity": int(event["severity"]),
        "asset": asset,
        "ret_pre1_post1": ret_pre1_post1,
        "ret_t_t3": ret_t_t3,
        "ret_t_t7": ret_t_t7,
        "vol_pre": vol_pre,
        "vol_post": vol_post,
        "vol_ratio": vol_ratio,
        "volume_pre_mean": volume_pre,
        "volume_post_mean": volume_post,
        "volume_ratio": volume_ratio,
        "sentiment_pre": sent_pre,
        "sentiment_post": sent_post,
        "sentiment_shift": sent_shift,
        "tvl_pre": tvl_pre,
        "tvl_post": tvl_post,
        "tvl_change_pct": tvl_change,
        "onchain_pre": onchain_pre,
        "onchain_post": onchain_post,
        "onchain_shift": onchain_shift,
    }


def main() -> pd.DataFrame:
    feats = read_parquet_safe(PROCESSED_DIR / "features.parquet")
    events = read_parquet_safe(PROCESSED_DIR / "events.parquet")
    if feats.empty or events.empty:
        log.error("Cannot run event study: features or events missing")
        return pd.DataFrame()

    sent = feats[["date", "sentiment_score"]].drop_duplicates("date")
    liq = feats[["date", "tvl_usd"]].drop_duplicates("date")
    onchain = feats[["date", "asset", "onchain_activity_index"]]

    rows = []
    for asset, asset_df in feats.groupby("asset"):
        asset_df = asset_df.sort_values("date")
        for _, ev in events.iterrows():
            row = study_event(ev, asset_df, sent, liq, onchain)
            rows.append(row)
    es = pd.DataFrame(rows)

    # Composite impact score: |ret_t_t7| + max(0, vol_ratio - 1)
    es["impact_score"] = es["ret_t_t7"].abs().fillna(0) + (es["vol_ratio"].fillna(1) - 1).clip(lower=0)
    out = PROCESSED_DIR / "event_study.parquet"
    write_parquet(es, out)
    log.info("Event study: %d rows -> %s", len(es), out)

    # Top-10 most impactful overall
    top10 = es.sort_values("impact_score", ascending=False).head(20)
    write_parquet(top10, PROCESSED_DIR / "event_study_top.parquet")

    # Event-type x asset pivot of mean impact
    pivot = es.pivot_table(index="event_type", columns="asset", values="impact_score", aggfunc="mean").reset_index()
    write_parquet(pivot, PROCESSED_DIR / "event_study_typeasset.parquet")
    return es


if __name__ == "__main__":
    main()
