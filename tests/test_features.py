"""Sanity tests for feature engineering and regime classification."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.market_features import add_cross_asset_features, add_market_features, add_sentiment_return_correlation
from src.features.regime_classifier import classify_row
from src.config import REGIME_PARAMS


def _toy_market(n: int = 60, asset: str = "BTC", seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rets = rng.normal(0.001, 0.03, n)
    price = 100 * np.exp(np.cumsum(rets))
    return pd.DataFrame({
        "date": dates,
        "asset": asset,
        "price": price,
        "volume": rng.lognormal(20, 0.4, n),
    })


def test_market_features_no_lookahead():
    """Rolling features at t must depend only on prices through t (not t+1)."""
    df = _toy_market(40)
    enriched = add_market_features(df)
    # Mutate the LAST row's price; earlier rolling values must not change.
    df2 = df.copy()
    df2.loc[df2.index[-1], "price"] *= 1.5
    enriched2 = add_market_features(df2)
    pre = enriched.iloc[:-1].reset_index(drop=True)
    pre2 = enriched2.iloc[:-1].reset_index(drop=True)
    cols = ["rolling_7d_volatility", "rolling_30d_volatility", "rolling_30d_return", "drawdown"]
    for c in cols:
        assert pre[c].equals(pre2[c]), f"Lookahead detected in {c}"


def test_drawdown_non_positive():
    df = _toy_market(30)
    e = add_market_features(df)
    assert (e["drawdown"].dropna() <= 1e-12).all(), "Drawdown should be <= 0"


def test_volume_zscore_finite():
    df = _toy_market(60)
    e = add_market_features(df)
    finite = e["volume_zscore_30d"].dropna()
    assert np.isfinite(finite).all(), "Volume z-score must be finite where defined"


def test_regime_precedence_event_over_riskoff():
    """Event-driven should win over Risk-off when both fire."""
    row = pd.Series({
        "event_flag": 1,
        "days_to_next_event": 0,
        "days_since_event": 0,
        "rolling_7d_return": -0.10,  # large move
        "rolling_30d_return": -0.20,
        "rolling_30d_volatility": 1.0,
        "rolling_7d_volatility": 1.5,
        "drawdown": -0.30,
        "sentiment_score": 20,
        "liquidity_stress_score": 0.5,
        "onchain_activity_index": 0,
        "volume_spike_flag": 0,
        "volume_zscore_30d": 0.5,
        "tvl_7d_change_pct": -0.02,
    })
    label = classify_row(row, vol_low=0.5)
    assert label == "Event-driven", f"Expected Event-driven, got {label}"


def test_regime_precedence_liquidity_over_riskoff():
    row = pd.Series({
        "event_flag": 0,
        "days_to_next_event": 999,
        "days_since_event": 999,
        "rolling_7d_return": -0.05,
        "rolling_30d_return": -0.20,
        "rolling_30d_volatility": 0.6,
        "rolling_7d_volatility": 0.7,
        "drawdown": -0.30,
        "sentiment_score": 30,
        "liquidity_stress_score": 2.0,  # > threshold
        "onchain_activity_index": 0,
        "volume_spike_flag": 0,
        "volume_zscore_30d": 0,
        "tvl_7d_change_pct": -0.10,
    })
    label = classify_row(row, vol_low=0.5)
    assert label == "Liquidity Stress"


def test_regime_calm_default():
    row = pd.Series({
        "event_flag": 0,
        "days_to_next_event": 999,
        "days_since_event": 999,
        "rolling_7d_return": 0.005,
        "rolling_30d_return": 0.01,
        "rolling_30d_volatility": 0.20,  # low vol
        "rolling_7d_volatility": 0.18,
        "drawdown": -0.02,
        "sentiment_score": 50,
        "liquidity_stress_score": 0.1,
        "onchain_activity_index": 0,
        "volume_spike_flag": 0,
        "volume_zscore_30d": 0,
        "tvl_7d_change_pct": 0.0,
    })
    label = classify_row(row, vol_low=0.30)  # 0.20 <= 0.30
    assert label == "Calm"


def test_event_study_window_alignment():
    """Event-study t-1 to t+1 return must equal log(p_{t+1} / p_{t-1})."""
    from src.analysis.event_study import _ret_between
    df = _toy_market(40)
    enriched = add_market_features(df)
    enriched["log_return"] = np.log(enriched["price"] / enriched["price"].shift(1))
    ed = enriched["date"].iloc[20]
    expected = float(np.log(enriched.set_index("date").loc[ed + pd.Timedelta(days=1), "price"]
                            / enriched.set_index("date").loc[ed - pd.Timedelta(days=1), "price"]))
    actual = _ret_between(enriched, pd.Timestamp(ed), -1, 1)
    assert abs(actual - expected) < 1e-9


def test_market_breadth_and_sentiment_corr_features():
    """Cross-asset participation and rolling sentiment-return corr are generated cleanly."""
    btc = _toy_market(80, asset="BTC", seed=11)
    eth = _toy_market(80, asset="ETH", seed=12)
    feats = add_cross_asset_features(add_market_features(pd.concat([btc, eth], ignore_index=True)))
    assert "market_breadth_positive_7d" in feats.columns
    assert feats["market_breadth_positive_7d"].dropna().between(0, 1).all()

    dates = pd.date_range("2024-01-01", periods=80, freq="D")
    sent = pd.DataFrame({"date": dates, "sentiment_score": np.linspace(35, 75, 80)})
    feats = feats.merge(sent, on="date", how="left")
    feats = add_sentiment_return_correlation(feats)
    corr = feats["sentiment_return_corr_30d"].dropna()
    assert not corr.empty
    assert corr.between(-1, 1).all()


def test_event_study_extended_windows():
    """Extended event windows should align to calendar-close returns."""
    from src.analysis.event_study import study_event

    df = _toy_market(50)
    enriched = add_market_features(df)
    enriched["log_return"] = np.log(enriched["price"] / enriched["price"].shift(1))
    ed = enriched["date"].iloc[25]
    event = pd.Series({"date": ed, "event_type": "ETF", "event_name": "Toy event", "severity": 2})
    row = study_event(event, enriched, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    idx = enriched.set_index("date")

    expected_3 = float(np.log(idx.loc[ed + pd.Timedelta(days=3), "price"] / idx.loc[ed - pd.Timedelta(days=3), "price"]))
    expected_7 = float(np.log(idx.loc[ed + pd.Timedelta(days=7), "price"] / idx.loc[ed - pd.Timedelta(days=7), "price"]))
    drift = float(np.log(idx.loc[ed + pd.Timedelta(days=7), "price"] / idx.loc[ed + pd.Timedelta(days=3), "price"]))

    assert abs(row["ret_pre3_post3"] - expected_3) < 1e-9
    assert abs(row["ret_pre7_post7"] - expected_7) < 1e-9
    assert abs(row["post_event_drift_3_7"] - drift) < 1e-9


def test_demo_data_bootstrap_marker(tmp_path):
    """Demo bootstrap should stage samples and leave an explicit sample-mode marker."""
    from src.utils.demo_data import SAMPLE_MARKER_NAME, ensure_processed_data, is_sample_mode

    sample = tmp_path / "sample"
    processed = tmp_path / "processed"
    sample.mkdir()
    (sample / "features_sample.parquet").write_text("placeholder")

    assert ensure_processed_data(sample, processed) is True
    assert (processed / "features.parquet").exists()
    assert (processed / SAMPLE_MARKER_NAME).exists()
    assert is_sample_mode(sample, processed) is True
