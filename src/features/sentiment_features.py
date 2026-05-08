"""Sentiment features built from the Fear & Greed daily series."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_sentiment_features(sent: pd.DataFrame) -> pd.DataFrame:
    """Input columns: date, sentiment_score, sentiment_label."""
    df = sent.sort_values("date").copy()
    df["sentiment_score"] = df["sentiment_score"].astype(float)
    df["sentiment_3d_change"] = df["sentiment_score"].diff(3)
    df["sentiment_7d_change"] = df["sentiment_score"].diff(7)
    rolling_mean = df["sentiment_score"].rolling(30, min_periods=10).mean()
    rolling_std = df["sentiment_score"].rolling(30, min_periods=10).std()
    df["sentiment_zscore_30d"] = (df["sentiment_score"] - rolling_mean) / rolling_std.replace(0, np.nan)

    def regime(s: float) -> str:
        if pd.isna(s):
            return "Unknown"
        if s < 25:
            return "Extreme Fear"
        if s < 45:
            return "Fear"
        if s < 55:
            return "Neutral"
        if s < 75:
            return "Greed"
        return "Extreme Greed"

    df["sentiment_regime"] = df["sentiment_score"].apply(regime)
    return df[[
        "date",
        "sentiment_score",
        "sentiment_label",
        "sentiment_3d_change",
        "sentiment_7d_change",
        "sentiment_zscore_30d",
        "sentiment_regime",
    ]]
