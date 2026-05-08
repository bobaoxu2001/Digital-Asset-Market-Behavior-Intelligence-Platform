"""Load curated events calendar from CSV into a parquet for downstream use.

Output: data/processed/events.parquet
"""
from __future__ import annotations

import pandas as pd

from src.config import EVENTS_CSV, PROCESSED_DIR
from src.utils.io import write_parquet
from src.utils.logging import get_logger

log = get_logger(__name__)


def main() -> pd.DataFrame:
    if not EVENTS_CSV.exists():
        log.error("Events CSV missing: %s", EVENTS_CSV)
        return pd.DataFrame()
    df = pd.read_csv(EVENTS_CSV)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["severity"] = pd.to_numeric(df["severity"], errors="coerce").fillna(1).astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    path = PROCESSED_DIR / "events.parquet"
    write_parquet(df, path)
    log.info("Events: %d rows -> %s", len(df), path)
    return df


if __name__ == "__main__":
    main()
