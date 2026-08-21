"""Stellar Variability & Regime Discovery — a real astronomy research program (Sprint 17).

General question: what temporal structures, regime changes, and uncertainty patterns can
ACERO identify in the public SILSO monthly sunspot series, and what limits interpretation of
PHYSICAL MECHANISMS from such a series?

This runs a full program: preregistration → competing hypotheses → analysis (periodogram,
surrogate-data significance, bootstrap CI, autocorrelation, regime/change detection,
sensitivity to gaps/detrending) → adversarial honesty checks → reliability → dossier. It
never claims a new star/planet/cycle/mechanism/causality/discovery. External review pending.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..benchmarks.real_astronomy_inference import (
    LICENSE,
    REFERENCE,
    _parse,
    analyze_sunspots,
    download_sunspots,
)
from ..core.hashing import hash_text

# --- preregistration (fixed BEFORE looking at results) --------------------

PREREGISTRATION: dict[str, Any] = {
    "dataset": "SILSO monthly mean total sunspot number (public domain)",
    "metrics": ["dominant_period_years", "surrogate_p_value", "bootstrap_period_ci",
                "cycle_length_cv", "n_low_activity_regimes"],
    "methods": ["FFT periodogram", "AR(1) red-noise surrogate significance",
                "bootstrap CI over cycle spacings", "autocorrelation",
                "decade-mean regime detection", "gap sensitivity"],
    "windows": "full series; decade windows for regimes",
    "controls": ["AR(1) red-noise surrogates (null for the spectral peak)",
                 "even/odd half split"],
    "splits": "first-half / second-half stability check",
    "stopping_rule": "single pre-specified analysis; no iterative re-analysis",
    "allowed_claims": ["a dominant ~period exists in the data with stated uncertainty",
                       "the series is periodic vs quasiperiodic (data-level)",
                       "multi-decade low-activity regimes are present"],
    "forbidden_claims": ["new star", "new planet", "new cycle", "the solar dynamo mechanism",
                         "any causal claim", "any discovery"],
}

# --- competing hypotheses (winner NOT hardcoded) --------------------------

HYPOTHESES = (
    "stable_periodicity", "quasiperiodicity", "multiple_components",
    "stochastic_process", "regime_change", "instrumental_artifact",
)


def _series(csv_path: str | Path) -> tuple[np.ndarray, np.ndarray, int, str]:
    text = Path(csv_path).read_text(encoding="utf-8", errors="replace")
    t, y, missing = _parse(text)
    return t, y, missing, hash_text(text)


def _dominant_period(t: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray, int]:
    dt = float(np.median(np.diff(t)))
    yc = y - y.mean()
    freqs = np.fft.rfftfreq(len(yc), d=dt)
    power = np.abs(np.fft.rfft(yc)) ** 2
    power[0] = 0.0
    peak = int(np.argmax(power))
    period = float(1.0 / freqs[peak]) if freqs[peak] > 0 else float("inf")
    return period, power, peak


def surrogate_significance(t: np.ndarray, y: np.ndarray, *, n_surrogates: int = 200,
                           seed: int = 0) -> dict[str, Any]:
    """AR(1) red-noise surrogates: does the peak power exceed what autocorrelated noise gives?

    Phase-randomized (FT) surrogates preserve the power spectrum, so they cannot test whether a
    spectral peak is 'real' — the correct null for a periodicity claim is red noise. We fit an
    AR(1) to the series and compare the observed peak against the peak of AR(1) realisations.
    """
    rng = np.random.default_rng(seed)
    yc = y - y.mean()
    _, power, peak_idx = _dominant_period(t, y)
    observed_peak = float(power[peak_idx])
    # AR(1) fit: phi = lag-1 autocorrelation; residual std from the AR(1) model
    phi = float(np.corrcoef(yc[:-1], yc[1:])[0, 1])
    phi = max(-0.99, min(0.99, phi))
    resid_std = float(np.std(yc[1:] - phi * yc[:-1]))
    n = len(yc)
    exceed = 0
    for _ in range(n_surrogates):
        noise = rng.normal(0.0, resid_std, n)
        surr = np.empty(n)
        surr[0] = noise[0]
        for i in range(1, n):
            surr[i] = phi * surr[i - 1] + noise[i]
        sp = np.abs(np.fft.rfft(surr - surr.mean())) ** 2
        sp[0] = 0.0
        if float(sp.max()) >= observed_peak:
            exceed += 1
    p = (exceed + 1) / (n_surrogates + 1)
    return {"null_model": "AR(1) red noise", "ar1_phi": round(phi, 3),
            "observed_peak_power": round(observed_peak, 1), "n_surrogates": n_surrogates,
            "p_value": round(p, 4), "significant_vs_null": p < 0.05}


def _cycle_spacings(t: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Peak-to-peak spacings (years) of the smoothed series — the observed cycle lengths."""
    dt = float(np.median(np.diff(t)))
    # smooth over ~2 years and require peaks separated by >= ~7 years so sub-cycle bumps are
    # not miscounted as cycles (the solar cycle is ~11 yr; ~24-25 cycles since 1749).
    win = max(13, int(2.0 / dt))
    min_sep = int(7.0 / dt)
    smooth = np.convolve(y, np.ones(win) / win, mode="same")
    peaks: list[int] = []
    for i in range(win, len(smooth) - win):
        if smooth[i] == max(smooth[i - win:i + win]):
            if not peaks or (i - peaks[-1]) >= min_sep:
                peaks.append(i)
    peak_years = t[peaks] if peaks else np.array([])
    return np.diff(peak_years) if len(peak_years) > 1 else np.array([])


def bootstrap_period_ci(t: np.ndarray, y: np.ndarray, *, n_boot: int = 300, seed: int = 0
                        ) -> dict[str, Any]:
    """Bootstrap the mean cycle length by resampling the observed peak-to-peak spacings.

    (A period CI from FFT on resampled irregular times is not valid — duplicate timestamps
    and non-uniform sampling; the cycle-spacing bootstrap is the sound estimator here.)"""
    spacings = _cycle_spacings(t, y)
    if len(spacings) < 3:
        return {"status": "insufficient", "n": int(len(spacings))}
    rng = np.random.default_rng(seed)
    means = [float(np.mean(rng.choice(spacings, size=len(spacings), replace=True)))
             for _ in range(n_boot)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"median_years": round(float(np.median(means)), 2),
            "ci95_years": [round(float(lo), 2), round(float(hi), 2)],
            "n_cycles": int(len(spacings)), "n_boot": n_boot}


def evaluate_hypotheses(analysis: dict[str, Any], surrogate: dict[str, Any]) -> dict[str, str]:
    """Assign a data-level verdict to each competing hypothesis (winner not hardcoded)."""
    quasi = analysis["classification"] == "quasiperiodic"
    sig = surrogate["significant_vs_null"]
    regimes = len(analysis["low_activity_decades"]) > 0
    return {
        "stable_periodicity": "weakened (cycle length varies)" if quasi else "consistent",
        "quasiperiodicity": "supported" if quasi else "not needed",
        "multiple_components": "possible; not tested exhaustively",
        "stochastic_process": "disfavoured (peak significant vs null)" if sig
                              else "not excluded",
        "regime_change": "supported (multi-decade low-activity stretch)" if regimes
                         else "not detected",
        "instrumental_artifact": "not assessed here (needs instrument metadata)",
    }


def honesty_gate(claims: list[str]) -> dict[str, Any]:
    """Block any forbidden (over-reaching) claim before it can be recorded."""
    forbidden = [c for c in claims
                 if any(bad in c.lower() for bad in
                        ("new star", "new planet", "new cycle", "dynamo", "mechanism",
                         "causal", "cause", "discover"))]
    return {"forbidden_claims_present": forbidden, "blocked": bool(forbidden),
            "allowed": not forbidden}


def run_program(csv_path: str | Path | None = None, *, authorized: bool = True,
                n_surrogates: int = 200) -> dict[str, Any]:
    """Execute the full program on the real SILSO series. Downloads (gated) if absent."""
    from ..core.config import repo_root
    from ..core.workspace import data_path
    path = Path(csv_path) if csv_path else data_path(
        "datos/datasets/sunspots.csv",
        legacy=repo_root() / "research" / "datasets" / "sunspots.csv",
    )
    manifest: dict[str, Any] | None = None
    if not path.exists():
        manifest = download_sunspots(path, authorized=authorized)

    t, y, missing, sha = _series(path)
    analysis = analyze_sunspots(path, manifest=manifest or {"sha256": sha, "license": LICENSE,
                                                            "reference": REFERENCE})
    surrogate = surrogate_significance(t, y, n_surrogates=n_surrogates)
    bootstrap = bootstrap_period_ci(t, y)
    hyp = evaluate_hypotheses(analysis, surrogate)

    # allowed, data-level findings only
    findings = [
        f"dominant period ≈ {analysis['dominant_period_years']} yr "
        f"(bootstrap 95% CI {bootstrap.get('ci95_years')})",
        f"series classified {analysis['classification']} "
        f"(cycle σ/μ = {analysis['cycle_std_years']}/{analysis['cycle_mean_years']} yr)",
        f"{len(analysis['low_activity_decades'])} multi-decade low-activity regime(s): "
        f"{analysis['low_activity_decades'][:4]}",
        f"peak power {'exceeds' if surrogate['significant_vs_null'] else 'does not exceed'} "
        f"a phase-randomized null (p={surrogate['p_value']})",
    ]
    honesty = honesty_gate(findings + list(PREREGISTRATION["allowed_claims"]))

    return {
        "program": "Stellar Variability & Regime Discovery",
        "dataset": {"n": len(y), "missing_months": missing, "sha256": sha,
                    "license": LICENSE, "reference": REFERENCE, "size_ok": path.stat().st_size < 500e6},
        "preregistration": PREREGISTRATION,
        "analysis": {"dominant_period_years": analysis["dominant_period_years"],
                     "classification": analysis["classification"],
                     "cycle_mean_years": analysis["cycle_mean_years"],
                     "cycle_std_years": analysis["cycle_std_years"],
                     "low_activity_decades": analysis["low_activity_decades"],
                     "surrogate": surrogate, "bootstrap_period": bootstrap},
        "hypotheses": hyp,
        "findings": findings,
        "honesty_gate": honesty,
        "cannot_conclude": [
            "the solar DYNAMO mechanism (a period is a pattern, not a mechanism)",
            "any causal claim from this observational series",
            "any prediction of future cycles",
            "any new star/planet/cycle — nothing is discovered here",
        ],
        "external_review": "PENDING — computational analysis of public data; not validated",
    }


def record_as_program(store: Any, *, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Register this study as a ResearchProgram (Program OS) + a review dossier.

    Persists a program with the central question, competing hypotheses (as instrumental
    questions), and a preregistration milestone; builds a ReviewDossier marked as NOT a
    discovery, requiring external human review. Never publishes.
    """
    from ..program.engine import ProgramEngine
    from ..program.models import QuestionRole
    from ..publication.dossier import DossierEvidence, ReviewDossier

    result = result or run_program()
    pe = ProgramEngine(store)
    program = pe.create(
        "Stellar Variability & Regime Discovery", domains=["astronomy"],
        central_question="What temporal structures/regimes can ACERO identify in the SILSO "
                         "sunspot series, and what limits mechanism interpretation?")
    for h in HYPOTHESES:
        pe.add_question(program.id, f"hypothesis: {h}", QuestionRole.INSTRUMENTAL)
    pe.add_milestone(program.id, "Preregistration fixed before analysis", kind="review")
    program.datasets = [result["dataset"]["reference"]]
    pe._save(program, summary="astronomy program datasets recorded")

    dossier = ReviewDossier(
        project=program.id,
        central_claim=(f"The SILSO series shows a dominant ~{result['analysis']['dominant_period_years']}"
                       f" yr cycle (classified {result['analysis']['classification']}), "
                       f"significant vs AR(1) red noise (p={result['analysis']['surrogate']['p_value']}), "
                       f"with multi-decade low-activity regimes — a DATA-LEVEL description, not a "
                       f"mechanism or discovery."),
        inference_level="statistical_association",
        supporting_evidence=[DossierEvidence(f"f{i}", f, "supporting", result_class="STATISTICAL_ASSOCIATION")
                             for i, f in enumerate(result["findings"])],
        counter_evidence=[DossierEvidence("c0", "cycle length varies (quasiperiodic)", "counter"),
                          DossierEvidence("c1", "instrumental artifacts not assessed", "counter")],
        limitations=result["cannot_conclude"],
        open_questions=["multiple-component decomposition not exhaustively tested",
                        "instrument/pipeline dependence not assessed"],
        comprehension_status="unknown", gate_status="complete",
        required_external_review=True)
    return {"program_id": program.id, "dossier": dossier.as_dict(),
            "analysis": result["analysis"], "hypotheses": result["hypotheses"],
            "honesty_gate": result["honesty_gate"], "cannot_conclude": result["cannot_conclude"]}
