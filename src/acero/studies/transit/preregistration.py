"""Preregistration for the transit robustness program — hashed BEFORE analysis.

The preregistration fixes hypotheses, metrics, methods, thresholds, detrending,
period search, injection design, null tests, splits, false-positive scenarios,
stopping rules, and the allowed vs prohibited claims. Its SHA-256 is written to an
artifact before any pipeline runs, so the analysis cannot be silently redesigned
after seeing results.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ...core.config import repo_root

PREREGISTRATION: dict[str, Any] = {
    "program": "Exoplanet Transit Signal Robustness Program",
    "version": "1.0",
    "question": (
        "How robustly can ACERO recover a KNOWN transit signal (Kepler-8b) against "
        "noise, gaps, detrending choices, cadence, multiple testing and instrumental "
        "artifacts, and under what conditions must it abstain? This is NOT a search "
        "for a new planet."),
    "hypotheses": {
        "H0": "noise + stellar trend only (no transit-like periodic dip)",
        "H1": "a periodic signal that is not transit-like (e.g. sinusoidal variability)",
        "H2": "the known transit of Kepler-8b (P~3.5225 d)",
        "H3": "an instrumental artifact (quarter boundary / roll / safe-mode gap)",
        "H4": "red (correlated) noise producing spurious dips",
        "H5": "a flexible model that overfits detrending residuals",
        "H6": "data insufficient to distinguish the above",
    },
    "metrics": ["BLS_power", "transit_SNR", "recovered_period", "period_error",
                "depth", "duration", "recovery_rate", "false_positive_rate",
                "pipeline_period_agreement"],
    "methods": {
        "pipeline_A": "median detrend + astropy BoxLeastSquares (box statistic)",
        "pipeline_B": "polynomial-segment detrend + phase-dispersion minimization (PDM)",
        "note": "Two pipelines over the SAME data are NOT independent replication.",
    },
    "thresholds": {
        "detection_SNR": 7.0,
        "period_agreement_tol_frac": 0.01,
        "period_stability_tol_frac": 0.02,
        "max_false_positive_rate": 0.05,
        "min_recovery_for_claim": 0.8,
    },
    "detrending": {
        "A_median_window_points": 101,
        "B_poly_order": 2,
        "declared_before_analysis": True,
        "rule": "detrending windows/orders are fixed here; results are reported for "
                "ALL declared choices, never cherry-picked post hoc.",
    },
    "period_search": {"grid_min_days": 0.5, "grid_max_days": 10.0,
                      "durations_days": [0.05, 0.1, 0.15, 0.2]},
    "signal_injection": {
        "depths_frac": [0.002, 0.005, 0.009, 0.02],
        "periods_days": [2.0, 3.5225, 5.0, 7.3],
        "durations_hours": [2.0, 3.2, 4.0],
        "phases": [0.0, 0.25, 0.5],
        "measure": ["recovery_rate", "period_error", "false_positive_rate", "calibration"],
    },
    "null_tests": [
        "flux_shuffled (destroys time order)",
        "control_star (real other star, no known transit)",
        "no_transit_synthetic (noise + trend only)",
        "AR1_red_noise_surrogate",
        "inverted_transit (dips flipped to bumps)",
        "phase_randomized (DECLARED: preserves power spectrum; only a null for "
        "transit SHAPE, not for periodicity — not used to test periodicity)",
    ],
    "splits": {"train_test": "odd/even quarters where possible; injection uses held-out"
                             " noise realizations"},
    "false_positive_scenarios": ["stellar variability", "instrumental discontinuity",
                                 "cosmic-ray-like outlier", "eclipsing-binary-like signal",
                                 "red-noise dip", "detrending artifact"],
    "stopping_rules": {
        "period_grid_fixed_before_analysis": True,
        "no_iterative_threshold_tuning": True,
        "abstain_if": ["pipeline disagreement beyond tol", "period unstable across detrending",
                       "SNR < detection_SNR", "FPR > max_false_positive_rate",
                       "null not controlled", "multiple indistinguishable candidates"],
    },
    "allowed_claims": [
        "A transit-like periodic signal consistent with the known Kepler-8b ephemeris "
        "is recoverable in this public data under the declared methods.",
        "Injected signals of stated SNR are recovered at the measured rate.",
    ],
    "prohibited_claims": [
        "Discovery of a new planet.",
        "An injected signal is a real astrophysical observation.",
        "Two pipelines over the same data constitute independent replication.",
        "A single run confirms a belief in the World Model.",
    ],
}


def _artifact_path() -> Path:
    d = repo_root() / "research" / "artifacts" / "transit"
    d.mkdir(parents=True, exist_ok=True)
    return d / "preregistration.json"


def canonical_bytes() -> bytes:
    return json.dumps(PREREGISTRATION, sort_keys=True, separators=(",", ":")).encode()


def prereg_hash() -> str:
    return hashlib.sha256(canonical_bytes()).hexdigest()


def write_preregistration(*, created_at: str) -> dict[str, Any]:
    """Write the preregistration + its hash to an artifact (call BEFORE analysis)."""
    doc = {"preregistration": PREREGISTRATION, "sha256": prereg_hash(),
           "created_at": created_at,
           "note": "Hashed before any pipeline ran. Changing the plan changes this hash."}
    _artifact_path().write_text(json.dumps(doc, indent=2))
    return doc


def verify_unchanged() -> bool:
    """True if the on-disk preregistration hash matches the current plan."""
    p = _artifact_path()
    if not p.exists():
        return False
    saved = json.loads(p.read_text()).get("sha256")
    return saved == prereg_hash()
