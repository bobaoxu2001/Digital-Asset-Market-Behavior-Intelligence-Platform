"""Sample-data bootstrap and runtime-mode detection for the dashboard.

When the dashboard is deployed to an environment that does not run the
ingestion pipeline (e.g. Streamlit Community Cloud), `data/processed/` will
not exist. This module copies the small bundled sample parquets and JSON
into `data/processed/` so every dashboard page can render without API calls,
and exposes ``is_sample_mode()`` so UI components can show a runtime banner.

Public API
----------
- ``ensure_processed_data(sample_dir=None, processed_dir=None) -> bool``
- ``is_sample_mode(sample_dir=None, processed_dir=None) -> bool``
- ``SAMPLE_MARKER_NAME`` (the ``.sample_mode`` filename written when staging)

Notes
-----
- Both functions never raise. They catch and swallow IO/OS errors and return
  conservative booleans so they can be called freely at the top of every
  Streamlit page.
- Type hints intentionally use ``typing.Optional`` instead of PEP 604
  ``X | None`` to maximize compatibility across Python versions that
  Streamlit Cloud may run.
- This module never imports Streamlit.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from src.utils.logging import get_logger

log = get_logger(__name__)

SAMPLE_MARKER_NAME = ".sample_mode"

# Sample basename -> processed basename
_FILE_MAP = {
    # parquet files
    "features_sample.parquet":              "features.parquet",
    "event_study_sample.parquet":           "event_study.parquet",
    "event_study_typeasset_sample.parquet": "event_study_typeasset.parquet",
    "lead_lag_sample.parquet":              "lead_lag.parquet",
    "regime_conditional_sample.parquet":    "regime_conditional.parquet",
    "chain_tvl_view_sample.parquet":        "chain_tvl_view.parquet",
    "defi_protocol_tvl_sample.parquet":     "defi_protocol_tvl.parquet",
    "stablecoins_sample.parquet":           "stablecoins.parquet",
    "events_sample.parquet":                "events.parquet",
    # JSON
    "behavior_summary_sample.json":         "behavior_summary.json",
}


def _on_streamlit_cloud() -> bool:
    """Best-effort check for Streamlit Community Cloud runtime. Never raises."""
    try:
        if os.getenv("STREAMLIT_RUNTIME"):
            return True
        if os.getenv("STREAMLIT_SERVER_HEADLESS"):
            return True
        host = os.getenv("HOSTNAME", "")
        if host.startswith("streamlit"):
            return True
    except Exception:
        pass
    return False


def _resolve_dirs(sample_dir, processed_dir):
    """Resolve directory paths via src.config defaults; never raises."""
    if sample_dir is None or processed_dir is None:
        try:
            from src.config import PROCESSED_DIR, SAMPLE_DIR
            sample_dir = sample_dir or SAMPLE_DIR
            processed_dir = processed_dir or PROCESSED_DIR
        except Exception as e:
            log.warning("Could not resolve config paths: %s", e)
            # Fallback: deduce from this file's location.
            here = Path(__file__).resolve().parents[2]
            sample_dir = sample_dir or (here / "data" / "sample")
            processed_dir = processed_dir or (here / "data" / "processed")
    return Path(sample_dir), Path(processed_dir)


def is_sample_mode(sample_dir: Optional[Path] = None,
                   processed_dir: Optional[Path] = None) -> bool:
    """Return True if the dashboard is running on bundled sample data.

    True when any of the following hold:
        1. ``data/processed/.sample_mode`` exists, or
        2. the runtime is detected as Streamlit Cloud / a hosted environment
           and ``data/processed/features.parquet`` is missing (we cannot have
           run the local ingestion pipeline there), or
        3. ``features.parquet`` exists but no real pipeline marker is found
           (defensive: assume sample if we cannot prove otherwise on Cloud).

    Never raises.
    """
    try:
        _, processed_dir = _resolve_dirs(sample_dir, processed_dir)
        marker = processed_dir / SAMPLE_MARKER_NAME
        if marker.exists():
            return True
        sentinel = processed_dir / "features.parquet"
        if _on_streamlit_cloud() and not sentinel.exists():
            return True
        return False
    except Exception as e:  # never crash UI code
        log.warning("is_sample_mode() failed safely: %s", e)
        return False


def ensure_processed_data(sample_dir: Optional[Path] = None,
                          processed_dir: Optional[Path] = None) -> bool:
    """Stage bundled sample data into ``data/processed/`` if needed.

    Returns True if the runtime is in sample mode — either because this call
    staged files, or because a prior call already wrote the ``.sample_mode``
    marker. Returns False only when a real pipeline run produced the data
    (sentinel file present, marker absent).

    Never raises.
    """
    try:
        sample_dir, processed_dir = _resolve_dirs(sample_dir, processed_dir)
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
    except Exception as e:  # never crash app startup
        log.warning("ensure_processed_data() failed safely: %s", e)
        return False


# Backwards-compatible alias (defensive — some imports may use this name).
sample_mode = is_sample_mode

__all__ = [
    "SAMPLE_MARKER_NAME",
    "ensure_processed_data",
    "is_sample_mode",
    "sample_mode",
]
