"""Gestion simple des codes de verification email (memoire, usage unique)."""

from __future__ import annotations

import secrets
import time
from threading import Lock

_codes: dict[str, tuple[str, float, int]] = {}
_lock = Lock()


def issue_code(email: str, ttl_seconds: int = 900) -> str:
    """Genere un code a 6 chiffres pour un email (validite: 15 min par defaut)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    with _lock:
        _purge_expired()
        _codes[email.lower()] = (code, time.time() + ttl_seconds, 0)
    return code


def consume_code(email: str, code: str, max_attempts: int = 5) -> bool:
    """Valide puis consomme le code. Retourne False si invalide/expire/trop de tentatives."""
    key = email.lower()
    with _lock:
        _purge_expired()
        item = _codes.get(key)
        if not item:
            return False
        expected_code, expires_at, attempts = item
        if time.time() > expires_at:
            _codes.pop(key, None)
            return False
        if attempts >= max_attempts:
            _codes.pop(key, None)
            return False
        if code.strip() != expected_code:
            _codes[key] = (expected_code, expires_at, attempts + 1)
            return False
        _codes.pop(key, None)
        return True


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, (_, exp, _) in _codes.items() if exp <= now]
    for key in expired:
        _codes.pop(key, None)
