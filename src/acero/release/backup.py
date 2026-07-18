"""Local backup / verify / restore (Sprint 20).

Creates a self-contained backup of the ACERO database into a directory with a SHA-256
manifest, verifies integrity, and restores it. Local-only; never uploads anywhere. Restore
is tested (round-trip). A restore refuses if the backup fails verification.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import get_config
from ..core.hashing import hash_text


class BackupError(RuntimeError):
    """Raised on a corrupt/incompatible backup."""


def _db_path(cfg: Any = None) -> Path | None:
    cfg = cfg or get_config()
    url = cfg.abs_db_url()
    if url.startswith("sqlite:///"):
        p = url[len("sqlite:///"):]
        if p and p != ":memory:":
            return Path(p)
    return None


def _hash_file(path: Path) -> str:
    return hash_text(path.read_bytes().hex())


def create(dest_dir: str | Path, *, cfg: Any = None) -> dict[str, Any]:
    """Copy the DB (if present) into ``dest_dir`` with a manifest of file hashes."""
    from .. import __version__
    from ..core.schema_version import CURRENT_SCHEMA_VERSION
    out = Path(dest_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    db = _db_path(cfg)
    if db and db.exists():
        shutil.copy2(db, out / "acero.sqlite")
        files["acero.sqlite"] = _hash_file(out / "acero.sqlite")
    manifest = {"created_at": now_iso(), "acero_version": __version__,
                "schema_version": CURRENT_SCHEMA_VERSION, "files": files,
                "destination": "local_only"}
    (out / "backup_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify(backup_dir: str | Path) -> dict[str, Any]:
    """Recompute hashes and compare with the manifest. Returns an ok/failures report."""
    d = Path(backup_dir)
    manifest_path = d / "backup_manifest.json"
    if not manifest_path.exists():
        raise BackupError("no backup_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    failures = []
    for name, expected in manifest.get("files", {}).items():
        f = d / name
        if not f.exists():
            failures.append(f"missing {name}")
        elif _hash_file(f) != expected:
            failures.append(f"hash mismatch {name}")
    return {"ok": not failures, "failures": failures,
            "acero_version": manifest.get("acero_version"),
            "schema_version": manifest.get("schema_version")}


def restore(backup_dir: str | Path, *, cfg: Any = None) -> dict[str, Any]:
    """Restore the DB from a VERIFIED backup. Refuses if verification fails."""
    report = verify(backup_dir)
    if not report["ok"]:
        raise BackupError(f"backup failed verification: {report['failures']}")
    d = Path(backup_dir)
    db = _db_path(cfg)
    restored = False
    if db and (d / "acero.sqlite").exists():
        db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d / "acero.sqlite", db)
        restored = True
    return {"restored": restored, "target": str(db) if db else None,
            "acero_version": report["acero_version"],
            "schema_version": report["schema_version"]}


def verify_backup_roundtrip() -> dict[str, Any]:
    """Self-contained backup→verify→restore round-trip against a temp DB."""
    import tempfile

    from sqlalchemy import create_engine, text
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "src.sqlite"
        eng = create_engine(f"sqlite:///{db}", future=True)
        with eng.begin() as c:
            c.execute(text("CREATE TABLE t (id INTEGER)"))
            c.execute(text("INSERT INTO t VALUES (1),(2),(3)"))
        # independent config copies so the shared cached config is never mutated
        cfg = get_config().model_copy(deep=True)
        cfg.storage.db_url = f"sqlite:///{db}"
        bdir = Path(td) / "backup"
        create(bdir, cfg=cfg)
        vok = verify(bdir)["ok"]
        # restore into a fresh target
        db2 = Path(td) / "restored.sqlite"
        cfg2 = get_config().model_copy(deep=True)
        cfg2.storage.db_url = f"sqlite:///{db2}"
        rep = restore(bdir, cfg=cfg2)
        rok = rep["restored"] and db2.exists()
        rows = 0
        if rok:
            eng2 = create_engine(f"sqlite:///{db2}", future=True)
            with eng2.begin() as c:
                rows = int(c.execute(text("SELECT count(*) FROM t")).scalar_one())
    return {"backup_ok": bool(vok), "restore_ok": bool(rok and rows == 3), "rows": rows}
