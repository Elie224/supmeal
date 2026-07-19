"""Stockage en memoire des codes OAuth a usage unique (defense en profondeur contre les fuites de token dans l URL)."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

_codes: dict[str, tuple[str, float]] = {}
_lock = Lock()


def store_code(code: str, token: str, ttl: int = 60) -> None:
    with _lock:
        _purge_expired()
        _codes[code] = (token, time.time() + ttl)


def consume_code(code: str) -> str | None:
    with _lock:
        _purge_expired()
        item = _codes.pop(code, None)
        if not item:
            return None
        token, expires_at = item
        if time.time() > expires_at:
            return None
        return token


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, (_, exp) in _codes.items() if exp <= now]
    for k in expired:
        _codes.pop(k, None)
