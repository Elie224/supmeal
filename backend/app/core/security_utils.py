"""Helpers securite : validation des uploads, sanitization, CSRF."""

from __future__ import annotations

import re
from typing import Final

# Magic bytes (signatures) des formats image autorises
_IMAGE_SIGNATURES: Final[list[tuple[bytes, str]]] = [
    (b"\xFF\xD8\xFF", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),  # voir check supplementaire
]

_MAX_IMAGE_BYTES: Final[int] = 10 * 1024 * 1024  # 10 Mo hard cap, avant check settings

# Caracteres dangereux pour CSV / formula injection (Excel, LibreOffice)
_CSV_DANGEROUS_PREFIXES: Final[tuple[str, ...]] = ("=", "+", "-", "@")


def sniff_image(data: bytes) -> str | None:
    """Retourne l extension normalisee si data ressemble a une vraie image, sinon None.
    Bloque SVG, PHP, HTML, scripts en se basant sur les magic bytes.
    """
    if not data or len(data) < 8:
        return None
    if len(data) > _MAX_IMAGE_BYTES:
        return None
    # PNG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    # JPEG
    if data.startswith(b"\xFF\xD8\xFF"):
        return ".jpg"
    # GIF
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    # WebP: RIFF????WEBP
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


def safe_image_extension(declared_ext: str, sniffed: str) -> str:
    """Verifie que l extension declaree correspond aux magic bytes."""
    declared = declared_ext.lower().lstrip(".")
    sniffer = sniffed.lstrip(".")
    if declared not in {"jpg", "jpeg", "png", "gif", "webp"}:
        return "." + sniffer if sniffer else ".jpg"
    # jpeg <=> jpg
    if declared == "jpeg":
        declared = "jpg"
    if sniffer == "jpg" and declared == "jpg":
        return ".jpg"
    if declared != sniffer:
        # mismatch -> on force l extension reelle
        return "." + sniffer
    return "." + declared


def sanitize_csv_cell(value: str | None) -> str:
    """Neutralise les injections de formule CSV (=, +, -, @)."""
    if value is None:
        return ""
    v = str(value)
    if v and v[0] in _CSV_DANGEROUS_PREFIXES:
        # On prefixe avec une apostrophe (force en texte brut dans Excel/LibreOffice)
        return "'" + v
    return v


_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


def is_safe_username(value: str) -> bool:
    return bool(_USERNAME_RE.match(value))


def strip_html(value: str | None) -> str:
    """Supprime toutes les balises HTML / scripts pour defaut.
    Utilise pour les contenus rendus cote serveur dans le front React (defense en profondeur)."""
    if not value:
        return ""
    # Tres basique : interdit < et > consecutifs. Le front echappe deja via React.
    return re.sub(r"<[^>]*>", "", value).strip()
