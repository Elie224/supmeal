"""Verification de mots de passe compromis via l API HIBP (k-anonymity).

Le mot de passe complet n est JAMAIS transmis : on envoie les 5 premiers
caracteres du SHA-1 a https://api.pwnedpasswords.com/range/<prefix>.
L API renvoie les suffixes de hash connus et leur nombre d occurrences.
On cherche notre suffixe (apres les 5 premiers chars) dans la reponse.

En cas d echec reseau ou timeout, on laisse passer (fail-open pour l UX).
"""

from __future__ import annotations

import hashlib
import time
from threading import Lock

import httpx

_HIBP_URL = "https://api.pwnedpasswords.com/range"
_TIMEOUT = 2.0
_cache = {}
_cache_lock = Lock()
_CACHE_TTL = 3600
_suffixes_map = {}


def _hash_pw(password):
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def is_pwned(password):
    """Renvoie True si le password est dans la base HIBP."""
    if not password or len(password) < 4:
        return False
    digest = _hash_pw(password)
    prefix = digest[:5]
    suffix = digest[5:]

    now = time.time()
    with _cache_lock:
        cached = _cache.get(prefix)
        if cached and now - cached[1] < _CACHE_TTL:
            return suffix in _suffixes_map.get(prefix, set())

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_HIBP_URL + "/" + prefix, headers={"Add-Padding": "true"})
        if r.status_code != 200:
            return False
        suffixes = set()
        for line in r.text.splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                suffixes.add(parts[0].upper())
        pwned = suffix in suffixes
        with _cache_lock:
            _cache[prefix] = (pwned, now)
            _suffixes_map[prefix] = suffixes
        return pwned
    except Exception:
        return False
