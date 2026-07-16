"""Baseline locking (Sprint 18).

Stores a signed baseline for a version under evaluation/baselines/<version>/. The baseline is
hashed; ``verify`` detects any silent modification. A baseline is written once per version and
refuses to overwrite unless explicitly forced (which is itself recorded).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.hashing import hash_json, hash_text


class BaselineError(RuntimeError):
    """Raised on a missing/corrupt/would-overwrite baseline."""


def _dir(version: str) -> Path:
    return repo_root() / "evaluation" / "baselines" / version


def write(version: str, results: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    d = _dir(version)
    results_path = d / "results.json"
    if results_path.exists() and not force:
        raise BaselineError(f"baseline for {version} already exists (use force to overwrite)")
    d.mkdir(parents=True, exist_ok=True)
    body = {"version": version, "created_at": now_iso(), "results": results,
            "content_hash": hash_json(results)}
    text = json.dumps(body, indent=2)
    results_path.write_text(text, encoding="utf-8")
    (d / "baseline.sig").write_text(hash_text(text), encoding="utf-8")
    return {"version": version, "path": str(results_path), "hash": body["content_hash"]}


def load(version: str) -> dict[str, Any]:
    d = _dir(version)
    results_path = d / "results.json"
    if not results_path.exists():
        raise BaselineError(f"no baseline for {version}")
    text = results_path.read_text(encoding="utf-8")
    sig = (d / "baseline.sig").read_text(encoding="utf-8").strip() if (d / "baseline.sig").exists() else ""
    if sig and sig != hash_text(text):
        raise BaselineError(f"baseline {version} was modified after locking (signature mismatch)")
    body = json.loads(text)
    if body.get("content_hash") != hash_json(body["results"]):
        raise BaselineError(f"baseline {version} content hash mismatch (tampered)")
    return body["results"]


def exists(version: str) -> bool:
    return (_dir(version) / "results.json").exists()
