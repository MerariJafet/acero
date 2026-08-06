"""External validation + verification packet — the loop that earns EXTERNALLY_VALIDATED.

Covers the ways the claim could be faked: AI/self validation, stale attestations
(content changed after the check), failed reproductions, and tampered packets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from acero.publication.external_validation import (
    AttestationError,
    ExternalAttestation,
    is_externally_validated,
    list_attestations,
    record_attestation,
    validation_status,
)
from acero.publication.verification_packet import build_packet


@pytest.fixture(autouse=True)
def _root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_VALIDATION_ROOT", str(tmp_path / "validation"))


def _att(**over):
    base = {"validator": "Dra. Ruiz", "affiliation": "UNAM", "bundle_hash": "h1",
            "verdict": "reproduced"}
    base.update(over)
    return ExternalAttestation(**base)


# --- the anti-fake rules ------------------------------------------------------

def test_ai_cannot_validate_itself():
    for name in ("ACERO", "codex", "claude", "system"):
        with pytest.raises(AttestationError):
            record_attestation("p1", _att(validator=name))


def test_author_cannot_validate_own_work():
    with pytest.raises(AttestationError):
        record_attestation("p1", _att(validator="Merari"), author="merari")


def test_conflict_of_interest_rejected():
    with pytest.raises(AttestationError):
        record_attestation("p1", _att(independent=False))


def test_bad_verdict_rejected():
    with pytest.raises(AttestationError):
        record_attestation("p1", _att(verdict="looks fine"))


# --- the gate -----------------------------------------------------------------

def test_one_independent_reproduction_validates():
    record_attestation("p2", _att())
    st = validation_status("p2", current_bundle_hash="h1")
    assert st["externally_validated"] is True and st["independent_validators"] == 1
    assert is_externally_validated("p2", current_bundle_hash="h1") is True


def test_same_validator_twice_is_still_one_validator():
    record_attestation("p3", _att())
    record_attestation("p3", _att(notes="otra corrida"))
    st = validation_status("p3", current_bundle_hash="h1", required=2)
    assert st["independent_validators"] == 1 and st["externally_validated"] is False


def test_attestation_goes_stale_when_content_changes():
    record_attestation("p4", _att(bundle_hash="OLD"))
    st = validation_status("p4", current_bundle_hash="NEW")
    assert st["externally_validated"] is False and st["stale"] == 1
    assert any("obsoleta" in r for r in st["reasons"])


def test_failed_reproduction_is_preserved_but_never_validates():
    record_attestation("p5", _att(verdict="failed", notes="no reproduje"))
    st = validation_status("p5", current_bundle_hash="h1")
    assert st["externally_validated"] is False and st["failed"] == 1
    assert len(list_attestations("p5")) == 1        # negative evidence preserved


# --- the packet (what the third party actually receives) ----------------------

def _packet(tmp_path, content=b"print('RESULT_JSON: {}')\n"):
    src = tmp_path / "exp"
    src.mkdir(parents=True)
    (src / "script.py").write_bytes(content)
    (src / "result.json").write_text('{"verdict": "inconclusive"}', encoding="utf-8")
    return build_packet(src, tmp_path / "packet", title="Prueba", version="1.0")


def test_packet_is_self_contained_and_verifies_intact(tmp_path):
    info = _packet(tmp_path)
    out = Path(info["path"])
    for f in ("manifest.json", "verify.py", "VERIFY.md", "attestation.json"):
        assert (out / f).is_file()
    assert (out / "files" / "script.py").is_file()
    # the third party's one command — stdlib only, no ACERO import
    r = subprocess.run([sys.executable, "verify.py"], cwd=out,
                       capture_output=True, text=True)
    assert r.returncode == 0 and "INTACT" in r.stdout
    assert info["manifest_hash"] in r.stdout          # the hash to paste in the attestation


def test_packet_detects_tampering(tmp_path):
    info = _packet(tmp_path)
    out = Path(info["path"])
    (out / "files" / "script.py").write_text("print('cambiado')", encoding="utf-8")
    r = subprocess.run([sys.executable, "verify.py"], cwd=out,
                       capture_output=True, text=True)
    assert r.returncode == 1 and "TAMPERED" in r.stdout


def test_attestation_template_binds_to_the_packet(tmp_path):
    info = _packet(tmp_path)
    tmpl = json.loads((Path(info["path"]) / "attestation.json").read_text(encoding="utf-8"))
    assert tmpl["bundle_hash"] == info["manifest_hash"]


def test_full_loop_packet_to_validated(tmp_path):
    """expose → verify → attest → EXTERNALLY_VALIDATED."""
    info = _packet(tmp_path)
    h = info["manifest_hash"]
    record_attestation("p6", _att(validator="Dr. Chen", bundle_hash=h))
    assert is_externally_validated("p6", current_bundle_hash=h) is True
    # and if the author edits the artifacts afterwards, validation lapses
    assert is_externally_validated("p6", current_bundle_hash="other") is False


def test_manifest_hash_is_stable(tmp_path):
    a = _packet(tmp_path / "a")
    b = _packet(tmp_path / "b")
    assert a["manifest_hash"] == b["manifest_hash"]   # same content → same anchor
