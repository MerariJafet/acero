"""Sprint 25: reproduction bundle, tamper detection, review simulation, standalone."""

from __future__ import annotations

from pathlib import Path

from acero.core.config import repo_root
from acero.reproduction import independent, simulation
from acero.reproduction.bundle import build_bundle, verify_bundle


def _pkg() -> Path:
    return repo_root() / "reproduction" / "transit_kepler8b"


def test_standalone_package_has_no_acero_imports():
    pkg = _pkg()
    if not pkg.exists():
        import pytest
        pytest.skip("reproduction package not present")
    out = independent.package_is_standalone(pkg)
    assert out["standalone"] is True, f"ACERO imports found in {out['offenders']}"
    assert len(out["checked"]) >= 3


def test_standalone_package_ships_required_files():
    pkg = _pkg()
    if not pkg.exists():
        import pytest
        pytest.skip("reproduction package not present")
    required = ["README.md", "LICENSE", "CITATION.cff", "requirements.txt", "Dockerfile",
                "download_data.py", "analyze.py", "run_all.py", "expected_outputs.json",
                "negative_results.md", "review_form.md", "AI_DISCLOSURE.md"]
    for name in required:
        assert (pkg / name).exists(), f"missing {name}"


def test_bundle_build_and_clean_verify(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "b.txt").write_text("beta")
    b = build_bundle(tmp_path, title="t", version="2.1.0-rc1", commit="abc123",
                     ai_disclosure="AI assisted; not an author",
                     review_questions=["is it a discovery? (no)"])
    rep = verify_bundle(b, tmp_path)
    assert rep.ok is True and not rep.modified and not rep.missing


def test_bundle_detects_modification(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    b = build_bundle(tmp_path, title="t", version="v", commit="c",
                     ai_disclosure="x", review_questions=[])
    (tmp_path / "a.txt").write_text("tampered!")     # modify after building
    rep = verify_bundle(b, tmp_path)
    assert rep.ok is False and "a.txt" in rep.modified


def test_bundle_detects_missing_and_version_and_commit(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    b = build_bundle(tmp_path, title="t", version="1.0", commit="c1",
                     ai_disclosure="x", review_questions=[])
    (tmp_path / "a.txt").unlink()
    rep = verify_bundle(b, tmp_path, expected_version="2.0", expected_commit="c2")
    assert rep.ok is False
    assert "a.txt" in rep.missing
    assert rep.version_mismatch is True and rep.commit_mismatch is True


def test_bundle_signature_roundtrip_and_tamper(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    secret = b"local-secret"
    b = build_bundle(tmp_path, title="t", version="v", commit="c",
                     ai_disclosure="x", review_questions=[])
    b.sign(secret)
    assert verify_bundle(b, tmp_path, secret=secret).signature_valid is True
    b.files["a.txt"] = "0" * 64                      # forge a hash without re-signing
    rep = verify_bundle(b, tmp_path, secret=secret)
    assert rep.signature_valid is False              # manifest changed -> bad signature


def test_review_simulation_never_auto_trusts():
    s = simulation.run_simulation()
    assert s["n"] == 10
    assert s["any_auto_trusted"] is False
    assert s["invariant_no_auto_trust"] is True
    kinds = {r["kind"] for r in s["reviews"]}
    assert {"tampered", "wrong_version", "unsigned", "failed_reproduction",
            "conflict_of_interest", "missing_evidence"} <= kinds


def test_independent_state_never_external_replication():
    rec = independent.ReproductionRecord(
        package="transit_kepler8b", fresh_container=True, fresh_database=True,
        fresh_workspace=True, empty_caches=True, no_acero_imports=True,
        outputs={"period": 3.5233}, hash_drift=[], warnings=[])
    d = rec.as_dict()
    assert d["state"] == independent.MAX_STATE
    assert d["is_external_replication"] is False
    assert d["no_hash_drift"] is True
