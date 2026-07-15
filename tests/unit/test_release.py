"""Sprint 20 tests: backup/verify/restore round-trip, disaster recovery, manifest, acceptance."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine

from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.ledger.service import ResearchLedger
from acero.release import backup
from acero.release.manifest import build_manifest, final_acceptance


class _Cfg:
    """Minimal config double pointing at a temp sqlite DB."""

    def __init__(self, db_path):
        self._url = f"sqlite:///{db_path}"

    def abs_db_url(self):
        return self._url


def _make_db(path):
    eng = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(eng)
    led = ResearchLedger(make_session_factory(eng))
    led.create_project("backup test", domain="physics")
    return led


# --- backup round-trip ----------------------------------------------------

def test_backup_create_verify_restore_roundtrip(tmp_path):
    db = tmp_path / "acero.sqlite"
    _make_db(db)
    cfg = _Cfg(db)
    bdir = tmp_path / "backup"
    m = backup.create(bdir, cfg=cfg)
    assert "acero.sqlite" in m["files"]
    assert backup.verify(bdir)["ok"]
    r = backup.restore(bdir, cfg=cfg)
    assert r["restored"] is True


def test_disaster_recovery_from_corrupted_db(tmp_path):
    db = tmp_path / "acero.sqlite"
    _make_db(db)
    cfg = _Cfg(db)
    bdir = tmp_path / "bk"
    backup.create(bdir, cfg=cfg)
    db.write_text("CORRUPTED")                      # simulate a lost/corrupt DB
    backup.restore(bdir, cfg=cfg)
    # the restored DB is a valid ACERO ledger again
    from acero.ledger.db import make_session_factory as msf
    led = ResearchLedger(msf(create_engine(f"sqlite:///{db}", future=True)))
    assert len(led.list_projects()) == 1


def test_restore_refuses_corrupt_backup(tmp_path):
    db = tmp_path / "acero.sqlite"
    _make_db(db)
    cfg = _Cfg(db)
    bdir = tmp_path / "bk"
    backup.create(bdir, cfg=cfg)
    (bdir / "acero.sqlite").write_text("tampered")   # corrupt the backup itself
    assert not backup.verify(bdir)["ok"]
    with pytest.raises(backup.BackupError):
        backup.restore(bdir, cfg=cfg)


def test_verify_reports_missing_manifest(tmp_path):
    with pytest.raises(backup.BackupError):
        backup.verify(tmp_path)


def test_backup_manifest_is_local_only(tmp_path):
    db = tmp_path / "acero.sqlite"
    _make_db(db)
    backup.create(tmp_path / "bk", cfg=_Cfg(db))
    manifest = json.loads((tmp_path / "bk" / "backup_manifest.json").read_text())
    assert manifest["destination"] == "local_only"


# --- release manifest -----------------------------------------------------

def test_manifest_reports_rc_version_and_no_autopublish():
    m = build_manifest()
    assert m["version"].startswith("2.0.0-rc")
    assert m["security"]["auto_publication"] is False
    assert m["gate_rules"] >= 80 and m["n_packages"] >= 25
    assert m["known_issues"]                         # honest known issues listed


# --- final acceptance -----------------------------------------------------

def test_final_acceptance_runs_all_gauntlets():
    r = final_acceptance()
    assert set(r["gauntlets"]) == {"reliability", "chaos", "red_team", "mutation", "review"}
    assert r["all_gauntlets_passed"] is True
    # acceptance reports; it never self-approves a release
    assert r["verdict"] == "RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW"
    assert "human decides" in r["note"]


def test_acceptance_never_claims_discovery_or_publishes():
    note = final_acceptance()["note"].lower()
    assert "no auto-publication" in note and "no discovery" in note
