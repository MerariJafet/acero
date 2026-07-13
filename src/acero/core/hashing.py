"""Content hashing for provenance and reproducibility.

Every artifact (input, code, output) is addressed by a SHA-256 digest so a third
party can verify that what was recorded is what was executed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def hash_json(obj: Any) -> str:
    """Canonical hash of a JSON-serialisable object (sorted keys, no whitespace)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hash_text(payload)
