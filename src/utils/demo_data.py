"""Sample-data bootstrap for cloud-hosted dashboards.

When the dashboard is deployed to an environment that does not run the
ingestion pipeline (e.g. Streamlit Community Cloud), `data/processed/` will
not exist. This helper copies the small bundled sample parquets and JSON
into `data/processed/` so every dashboard page can render without running
any API calls.

Behavior:
- Idempotent. Once a stage occurs, a marker file `data/processed/.sample_mode`
  is written; subsequent calls detect this and short-circuit.
- Returns True whenever the runtime is in sample mode (either the helper just
  staged files, or `.sample_mode` is already present from a prior session).
- Returns False only when `data/processed/` was populated by a real pipeline
  run (no marker file present).
- Never raises. If a sample file is missing the function logs a warning and
  continues with the files it can stage.

The marker mechanism makes mode-detection survive across Streamlit Cloud
session restarts where the filesystem persists between requests but Python
process state does not.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from src.utils.logging import get_logger

log = get_logger(__name__)

SAMPLE_MARKER_NAME = ".sample_mode"


def _on_streamlit_cloud() -> bool:
    """Best-effort check for Streamlit Community Cloud runtime."""
    # Streamlit Cloud sets STREAMLIT_RUNTIME (and HOSTNAME starts with "streamlit").
    if os.getenv("STREAMLIT_RUNTIME"):
        return True
    host = os.getenv("HOSTNAME", "")
    if host.startswith("streamlit"):
        return True
    return False


def is_sample_mode(processed_dir: Path | None = None) -> bool:
    """Return True if the dashboard is running on bundled sample data.

    True when any of the following hold:
        - the `.sample_mode` marker file exists in `data/processed/`
        - the helper just staged sample files (handled by ensure_processed_data)
        - the runtime is detected as Streamlit Cloud and processed data was
          not produced by a real pipeline (no marker yet, but no real pipeline
          could have run on Cloud either).
    """
    if processed_dir is None:
        from src.config import PROCESSED_DIR
        processed_dir = PROCESSED_DIR
    marker = Path(processed_dir) / SAMPLE_MARKER_NAME
    if marker.exists():
        return True
    return False

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

    Returns True if the runtime is in sample mode — either because this call
    staged files, or because a prior call already wrote the `.sample_mode`
    marker. Returns False only when a real pipeline run produced the data
    (sentinel file present, marker absent).
    """
    if sample_dir is None or processed_dir is None:
        from src.config import PROCESSED_DIR, SAMPLE_DIR
        sample_dir = sample_dir or SAMPLE_DIR
        processed_dir = processed_dir or PROCESSED_DIR

    sample_dir = Path(sample_dir)
    processed_dir = Path(processed_dir)
    marker = processed_dir / SAMPLE_MARKER_NAME
    sentinel = processed_dir / "features.parquet"

    # Case 1: marker file already present -> sample mode persists across sessions
    if marker.exists():
        return True

    # Case 2: real pipeline output present, no marker -> not sample mode
    if sentinel.exists():
        return False

    # Case 3: nothing present -> stage samples
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

    # Always write the marker once we have staged any sample file, so subsequent
    # sessions reliably detect sample mode without recopying.
    try:
        marker.write_text("sample mode active\n")
    except OSError as e:
        log.warning("Could not write %s marker: %s", marker, e)

    if copied:
        log.info("Demo mode: staged %d sample file(s) into %s", copied, processed_dir)
    return True
