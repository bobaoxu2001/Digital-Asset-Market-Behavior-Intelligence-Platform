"""Sample-data bootstrap for cloud-hosted dashboards.

When the dashboard is deployed to an environment that does not run the
ingestion pipeline (e.g. Streamlit Community Cloud), `data/processed/` will
not exist. This helper copies the small bundled sample parquets and JSON
into `data/processed/` so every dashboard page can render without running
any API calls.

Behavior:
- Idempotent. If `data/processed/features.parquet` already exists, the
  helper does nothing.
- Returns True if a copy occurred (i.e. the runtime is in sample mode),
  False otherwise. The dashboard uses this to surface a small note.
- Never raises. If a sample file is missing the function logs a warning
  and continues with the files it can stage.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from src.utils.logging import get_logger

log = get_logger(__name__)

# Sample basename -> processed basename
_FILE_MAP = {
    # parquet files
    "features_sample.parquet":            "features.parquet",
    "event_study_sample.parquet":         "event_study.parquet",
    "event_study_typeasset_sample.parquet": "event_study_typeasset.parquet",
    "lead_lag_sample.parquet":            "lead_lag.parquet",
    "regime_conditional_sample.parquet":  "regime_conditional.parquet",
    "chain_tvl_view_sample.parquet":      "chain_tvl_view.parquet",
    "defi_protocol_tvl_sample.parquet":   "defi_protocol_tvl.parquet",
    "stablecoins_sample.parquet":         "stablecoins.parquet",
    "events_sample.parquet":              "events.parquet",
    # JSON
    "behavior_summary_sample.json":       "behavior_summary.json",
}


def ensure_processed_data(sample_dir: Path | None = None,
                          processed_dir: Path | None = None) -> bool:
    """Stage bundled sample data into `data/processed/` if needed.

    Returns True if sample data was copied (sample mode active),
    False if processed data was already present.
    """
    # Lazy import to avoid a circular dependency: config imports this module
    # at module level only via the dashboard startup hook; passing dirs
    # explicitly is supported too for tests.
    if sample_dir is None or processed_dir is None:
        from src.config import PROCESSED_DIR, SAMPLE_DIR
        sample_dir = sample_dir or SAMPLE_DIR
        processed_dir = processed_dir or PROCESSED_DIR

    sample_dir = Path(sample_dir)
    processed_dir = Path(processed_dir)

    sentinel = processed_dir / "features.parquet"
    if sentinel.exists():
        return False  # full pipeline output already present; nothing to do

    if not sample_dir.exists():
        log.warning("Sample directory %s missing; cannot bootstrap demo data", sample_dir)
        return False

    processed_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src_name, dst_name in _FILE_MAP.items():
        src = sample_dir / src_name
        dst = processed_dir / dst_name
        if dst.exists():
            continue
        if not src.exists():
            log.warning("Sample file missing, skipping: %s", src.name)
            continue
        try:
            shutil.copy2(src, dst)
            copied += 1
        except OSError as e:
            log.warning("Failed to copy %s -> %s: %s", src.name, dst.name, e)

    if copied:
        log.info("Demo mode: staged %d sample file(s) into %s", copied, processed_dir)
    return copied > 0
