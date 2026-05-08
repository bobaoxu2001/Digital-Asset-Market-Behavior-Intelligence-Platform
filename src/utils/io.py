"""Parquet/CSV/JSON IO helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_parquet_safe(path: Path) -> pd.DataFrame:
    """Return DataFrame or empty DataFrame if file missing."""
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def read_json_safe(path: Path) -> Any:
    if not Path(path).exists():
        return None
    with open(path, "r") as f:
        return json.load(f)
