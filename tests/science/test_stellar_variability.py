"""Sprint 17 science test: the real astronomy program on public SILSO data.

Runs on the cached public-domain SILSO series (gitignored). Skips if the dataset is absent
(no network in the test env) — the program itself downloads it gated when authorized.
"""

from __future__ import annotations

import numpy as np
import pytest

from acero.core.config import repo_root
from acero.studies.stellar_variability import (
    HYPOTHESES,
    PREREGISTRATION,
    bootstrap_period_ci,
    honesty_gate,
    run_program,
    surrogate_significance,
)

_CSV = repo_root() / "research" / "datasets" / "sunspots.csv"
_have_data = _CSV.exists()
skip = pytest.mark.skipif(not _have_data, reason="SILSO dataset not cached (offline)")


def test_prereg_forbids_discovery_and_mechanism():
    forb = " ".join(PREREGISTRATION["forbidden_claims"]).lower()
    assert "discovery" in forb and "dynamo" in forb and "causal" in forb


def test_hypotheses_do_not_hardcode_a_winner():
    assert "stochastic_process" in HYPOTHESES and "instrumental_artifact" in HYPOTHESES
    assert len(HYPOTHESES) >= 6


def test_honesty_gate_blocks_forbidden_claims():
    assert honesty_gate(["we discovered a new solar cycle"])["blocked"]
    assert honesty_gate(["the dynamo mechanism is confirmed"])["blocked"]
    assert not honesty_gate(["a ~11 yr cycle exists in the data with a CI"])["blocked"]


def test_ar1_surrogate_is_the_null_not_phase_randomization():
    # synthetic: a clear sinusoid over red-ish noise should be significant vs AR(1)
    t = np.linspace(1749, 2020, 3000)
    y = 50 + 40 * np.sin(2 * np.pi * t / 11.0) + np.random.default_rng(0).normal(0, 10, len(t))
    s = surrogate_significance(t, y, n_surrogates=100)
    assert s["null_model"] == "AR(1) red noise"
    assert s["significant_vs_null"] is True


def test_bootstrap_reports_cycle_count_and_ci():
    t = np.linspace(1749, 2020, 3000)
    y = 50 + 40 * np.sin(2 * np.pi * t / 11.0)
    b = bootstrap_period_ci(t, y)
    assert b["n_cycles"] >= 20                       # ~24 cycles over 271 years
    lo, hi = b["ci95_years"]
    assert lo <= 11.0 <= hi                          # CI contains the true period


@skip
def test_real_silso_dominant_cycle_and_regime():
    r = run_program(n_surrogates=100)
    a = r["analysis"]
    assert 10.0 <= a["dominant_period_years"] <= 12.5       # the ~11 yr solar cycle
    assert a["classification"] == "quasiperiodic"
    assert a["low_activity_decades"]                        # Dalton-minimum-like stretch
    # bootstrap CI must be internally consistent with the FFT period
    lo, hi = a["bootstrap_period"]["ci95_years"]
    assert lo <= a["dominant_period_years"] <= hi
    # peak is significant vs a red-noise null
    assert a["surrogate"]["significant_vs_null"] is True


@skip
def test_real_program_refuses_discovery_claims():
    r = run_program(n_surrogates=50)
    assert not r["honesty_gate"]["blocked"]                 # allowed claims only
    joined = " ".join(r["cannot_conclude"]).lower()
    assert "dynamo" in joined and "discover" in joined
    assert r["external_review"].startswith("PENDING")
