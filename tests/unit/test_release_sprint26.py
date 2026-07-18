"""Sprint 26: version, security audit, backup roundtrip, burn-in, demo, acceptance."""

from __future__ import annotations

import os

import pytest


def test_version_is_2_1_0_rc1():
    from acero import __version__
    assert __version__ == "2.1.0-rc1"


def test_security_audit_all_ok():
    from acero.release.security_audit import security_audit
    a = security_audit()
    assert a["all_ok"] is True, f"failures: {a['failures']}"
    assert a["n"] >= 10


def test_backup_roundtrip():
    from acero.release.backup import verify_backup_roundtrip
    r = verify_backup_roundtrip()
    assert r["backup_ok"] is True
    assert r["restore_ok"] is True
    assert r["rows"] == 3


def test_release_burnin_no_duplication(tmp_path):
    from acero.release.burnin import run_release_burnin
    r = run_release_burnin(str(tmp_path / "b.sqlite"), n_tasks=30, n_workers=3)
    assert r["no_duplication"] is True
    assert r["done"] == 30 - r["cancelled"]
    assert r["total_processed"] <= 30                 # never processed more than enqueued


def test_demo_full_runs_and_claims_no_discovery():
    from acero.cli.demo import run_full_demo
    lines = list(run_full_demo())
    text = "\n".join(lines)
    assert "program" in text and "dossier" in text
    assert "no discovery claimed" in text.lower()
    assert "BLOCKED" in text                           # gate blocks invalid artifact
    assert "auto-publish=OFF" in text


def test_manifest_known_issues_are_honest():
    from acero.release.manifest import build_manifest
    m = build_manifest()
    joined = " ".join(m["known_issues"]).lower()
    assert "not external replication" in joined
    assert "abstains" in joined                        # transit abstention disclosed
    assert m["version"] == "2.1.0-rc1"


@pytest.mark.slow
def test_acceptance_matrix_all_pass():
    if os.environ.get("ACERO_SKIP_SLOW"):
        pytest.skip("slow")
    from acero.release.acceptance import acceptance_matrix
    m = acceptance_matrix()
    assert m["all_pass"] is True, f"blockers: {m['blockers']}"
    assert m["verdict"] == "RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW"
    assert m["n"] >= 20
