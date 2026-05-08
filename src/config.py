"""Central configuration loader.

Reads config/config.yaml plus .env. Exposes module-level constants used by every
ingest/feature/analysis script. Never logs API keys.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

with open(ROOT / "config" / "config.yaml", "r") as f:
    CFG: dict[str, Any] = yaml.safe_load(f)

# Paths
RAW_DIR = ROOT / CFG["paths"]["raw"]
PROCESSED_DIR = ROOT / CFG["paths"]["processed"]
SAMPLE_DIR = ROOT / CFG["paths"]["sample"]
EVENTS_CSV = ROOT / CFG["paths"]["events_csv"]
for d in (RAW_DIR, PROCESSED_DIR, SAMPLE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Date range
DATE_START = CFG["date_range"]["start"]
DATE_END = CFG["date_range"]["end"]  # may be None

# Assets
CORE_ASSETS = CFG["assets"]["core"]
EXTENDED_ASSETS = CFG["assets"]["extended"]
ALL_ASSETS = CORE_ASSETS + EXTENDED_ASSETS

DEFI_CHAINS = CFG["defi"]["chains"]
DEFI_PROTOCOLS = CFG["defi"]["protocols"]
STABLECOINS = CFG["defi"]["stablecoins"]

FRED_SERIES = CFG["macro"]["fred_series"]
YF_MACRO = CFG["macro"]["yf_fallback"]

HTTP_TIMEOUT = CFG["http"]["timeout_sec"]
HTTP_RETRIES = CFG["http"]["retries"]
HTTP_BACKOFF = CFG["http"]["backoff_sec"]

REGIME_PARAMS = CFG["regime"]

# API keys (loaded from .env; may be empty strings)
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "").strip()


def has_key(name: str) -> bool:
    """Return True if the named key is present and non-empty (never echoes the value)."""
    return bool(globals().get(name, "") or "")
