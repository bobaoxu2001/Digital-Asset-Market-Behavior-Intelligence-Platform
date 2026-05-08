"""HTTP fetch with retries, exponential backoff, and on-disk caching of raw responses."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import requests

from src.config import HTTP_BACKOFF, HTTP_RETRIES, HTTP_TIMEOUT, RAW_DIR
from src.utils.logging import get_logger

log = get_logger(__name__)


def _cache_key(url: str, params: Optional[dict]) -> str:
    raw = url + "|" + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def http_get_json(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    cache_namespace: str = "misc",
    cache_filename: Optional[str] = None,
    use_cache: bool = True,
) -> Optional[Any]:
    """GET a URL with retries; cache JSON responses under data/raw/<namespace>/.

    Returns parsed JSON or None on terminal failure. Never raises for the caller.
    """
    cache_dir = RAW_DIR / cache_namespace
    cache_dir.mkdir(parents=True, exist_ok=True)
    fname = cache_filename or (_cache_key(url, params) + ".json")
    cache_path = cache_dir / fname

    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception:
            pass  # fall through to refetch

    last_err: Optional[str] = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError:
                    log.warning("Non-JSON response from %s", url)
                    return None
                with open(cache_path, "w") as f:
                    json.dump(data, f)
                return data
            elif r.status_code in (429, 502, 503, 504):
                last_err = f"HTTP {r.status_code}"
                time.sleep(HTTP_BACKOFF * attempt)
                continue
            else:
                last_err = f"HTTP {r.status_code}"
                log.warning("Request to %s failed: %s", url, last_err)
                return None
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(HTTP_BACKOFF * attempt)
    log.warning("Giving up on %s after %d attempts (%s)", url, HTTP_RETRIES, last_err)
    return None
