"""Sprint 24: real Kepler-8 data recovery (network/cache-gated).

Skips if the FITS aren't cached and can't be downloaded, so the gate stays green
offline. When data are available, asserts BOTH pipelines recover the known
Kepler-8b period and that the manifest records provenance + hashes.
"""

from __future__ import annotations

import numpy as np
import pytest

from acero.studies.transit import data
from acero.studies.transit import pipelines as pl

KEPLER8B = 3.52254


def _target():
    try:
        s = data.load_series(data.TARGET_KIC, data.TARGET_QUARTERS)
    except Exception as exc:  # noqa: BLE001 - offline / archive unavailable
        pytest.skip(f"Kepler data unavailable: {exc}")
    if len(s["flux"]) < 1000:
        pytest.skip("insufficient cached Kepler data")
    return s


def test_both_pipelines_recover_known_period():
    s = _target()
    t = np.array(s["time"])
    f = np.array(s["flux"])
    a = pl.pipeline_a(t, f)
    b = pl.pipeline_b(t, f)
    assert abs(a.period - KEPLER8B) / KEPLER8B < 0.005
    assert abs(b.period - KEPLER8B) / KEPLER8B < 0.005
    assert pl.period_agreement(a, b)["agree_1pct"] is True
    assert a.snr > 20                                   # a strong, real transit


def test_manifest_records_provenance():
    doc = data.acquire_program(downloaded_at="test")
    assert doc["license"].startswith("Public domain")
    assert doc["total_bytes"] < 500_000_000            # under per-dataset limit
    for m in doc["manifests"]:
        assert len(m["sha256"]) == 64
        assert m["source_url"].startswith("https://archive.stsci.edu")
        assert m["role"] in ("science", "control")


def test_control_star_does_not_show_target_transit():
    from acero.studies.transit import nulls
    try:
        c = data.load_series(data.CONTROL_KIC, data.CONTROL_QUARTERS)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"control data unavailable: {exc}")
    ct = np.array(c["time"])
    cf = np.array(c["flux"])
    out = nulls.null_control_star(ct, cf, KEPLER8B)
    assert out["pass"] is True          # control must NOT match Kepler-8b's period


def test_program_end_to_end_makes_no_discovery_and_builds_dossier():
    _target()                            # skips offline
    from acero.studies.transit import dossier, program
    from acero.studies.transit import preregistration as prereg
    prereg.write_preregistration(created_at="test")
    r = program.run_program(downloaded_at="test", full_injection=False)
    # recovery of a KNOWN transit — never a discovery
    assert r["claims"]["is_discovery"] is False
    assert r["period_recovery_frac_error"] < 0.005
    # the forced hard case MUST abstain (real abstention preserved)
    assert r["abstention_forced_hard_case"]["abstain"] is True
    # dossier tree materializes with negative results preserved
    root = dossier.build_dossier(r)
    assert (root / "negative_results" / "negative_results.md").exists()
    assert (root / "preregistration" / "preregistration.json").exists()
    assert (root / "publication_candidate" / "status.md").exists()
    neg = (root / "negative_results" / "negative_results.md").read_text()
    assert "preserved" in neg.lower()


def test_record_as_program_is_not_a_discovery(session_factory):
    _target()
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.studies.transit import program
    store = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    out = program.record_as_program(store)
    assert out["is_discovery"] is False
    assert out["dossier"]["required_external_review"] is True


def test_cleanroom_reproduces(tmp_path):
    _target()
    from acero.studies.transit import cleanroom
    rep = cleanroom.reproduce(tmp_path / "fresh")
    assert rep["reproduced_known_period"] is True
    assert rep["no_hash_drift"] is True
    assert "NOT a discovery" in rep["note"]
