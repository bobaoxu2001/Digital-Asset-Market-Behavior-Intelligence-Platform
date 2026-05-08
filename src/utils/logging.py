"""Lightweight logging setup. Avoids leaking API keys or query params containing them."""
from __future__ import annotations

import logging
import re

_KEY_PATTERN = re.compile(r"(api[_-]?key|apikey|x-cg-demo-api-key)=([^&\s]+)", re.IGNORECASE)


class _SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _KEY_PATTERN.sub(r"\1=***", record.msg)
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    h.addFilter(_SecretFilter())
    logger.addHandler(h)
    logger.propagate = False
    return logger
