"""Stable, human-inspectable IDs for scientific objects.

Format: ``<prefix>_<26-char base32 ULID-like>`` where the leading component is a
millisecond timestamp so IDs sort chronologically. IDs are opaque but greppable.
"""

from __future__ import annotations

import os
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32 (no I,L,O,U)


def _encode(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        value, rem = divmod(value, 32)
        chars.append(_ALPHABET[rem])
    return "".join(reversed(chars))


def _now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str, *, now_ms: int | None = None, entropy: bytes | None = None) -> str:
    """Generate a new prefixed, time-sortable ID.

    ``now_ms`` and ``entropy`` are injectable for deterministic tests.
    """
    ts = _now_ms() if now_ms is None else now_ms
    ent = os.urandom(10) if entropy is None else entropy
    ts_part = _encode(ts, 10)
    ent_int = int.from_bytes(ent[:10].ljust(10, b"\x00"), "big")
    ent_part = _encode(ent_int, 16)
    return f"{prefix}_{ts_part}{ent_part}"


def is_valid(value: str, prefix: str | None = None) -> bool:
    """Validate an ID's shape (and optional prefix)."""
    if "_" not in value:
        return False
    pfx, body = value.split("_", 1)
    if prefix is not None and pfx != prefix:
        return False
    if not pfx or len(body) != 26:
        return False
    return all(c in _ALPHABET for c in body)
