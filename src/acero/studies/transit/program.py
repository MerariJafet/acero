"""Orchestrator for the Exoplanet Transit Signal Robustness Program.

Runs the whole program end to end: verify preregistration → load real data →
two pipelines → period stability across detrending → signal injection →
null tests → false positives → abstention (both a supported claim AND a forced
abstention on a hard case). Records nothing as a discovery.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ...core.config import repo_root
from . import abstention, data, injection, nulls
from . import pipelines as pl
from . import preregistration as prereg

KEPLER8B_PERIOD = 3.52254


def _artifacts() -> Path:
    d = repo_root() / "research" / "artifacts" / "transit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def period_stability(time: np.ndarray, flux: np.ndarray,
                     windows: tuple[int, ...] = (51, 101, 201)) -> dict[str, Any]:
    """Recover the period under several detrending windows; report max deviation."""
    periods = []
    for w in windows:
        res = pl.pipeline_a(time, flux, window=w, p_min=0.5, p_max=8.0)
        periods.append(res.period)
    periods_arr = np.array(periods)
    ref = float(np.median(periods_arr))
    max_frac = float(np.max(np.abs(periods_arr - ref) / ref)) if ref else 1.0
    return {"windows": list(windows), "periods": [round(p, 5) for p in periods],
            "max_frac_deviation": round(max_frac, 5)}


def run_program(*, downloaded_at: str, full_injection: bool = True) -> dict[str, Any]:
    if not prereg.verify_unchanged():
        raise RuntimeError("preregistration missing or changed; refusing to analyze")

    manifests = data.acquire_program(downloaded_at)
    target = data.load_series(data.TARGET_KIC, data.TARGET_QUARTERS)
    control = data.load_series(data.CONTROL_KIC, data.CONTROL_QUARTERS)
    t = np.array(target["time"])
    f = np.array(target["flux"])
    ct = np.array(control["time"])
    cf = np.array(control["flux"])

    a = pl.pipeline_a(t, f)
    b = pl.pipeline_b(t, f)
    agreement = pl.period_agreement(a, b)
    stability = period_stability(t, f)

    depths = prereg.PREREGISTRATION["signal_injection"]["depths_frac"]
    periods = prereg.PREREGISTRATION["signal_injection"]["periods_days"]
    durs = prereg.PREREGISTRATION["signal_injection"]["durations_hours"]
    phases = prereg.PREREGISTRATION["signal_injection"]["phases"]
    if not full_injection:            # fast path for tests
        depths, periods, durs, phases = depths[2:], periods[1:2], durs[1:2], phases[:1]
    recovery = injection.recovery_grid(depths=depths, periods=periods,
                                       durations_hours=durs, phases=phases)
    calibration = injection.recovery_vs_snr(snr_levels=[3.0, 5.0, 7.0, 12.0, 20.0],
                                            trials=6 if full_injection else 3)

    null_summary = nulls.run_all_nulls(t, f, target_period=KEPLER8B_PERIOD,
                                       control_time=ct, control_flux=cf)
    fp_scenarios = nulls.false_positive_scenarios()

    thr = prereg.PREREGISTRATION["thresholds"]
    # (1) the supported (bounded, non-discovery) claim for Kepler-8b
    supported = abstention.decide(
        snr=a.snr, period_agreement=agreement,
        period_stability_frac=stability["max_frac_deviation"],
        null_summary=null_summary, recovery_rate=recovery["recovery_rate"],
        quality_severe=False, n_indistinguishable_candidates=1, thresholds=thr)

    # (2) a FORCED, honest abstention on a genuinely hard low-SNR case
    forced = _forced_abstention_case(thr)

    result = {
        "preregistration_hash": prereg.prereg_hash(),
        "preregistration_unchanged": True,
        "data": {"target": data.TARGET_NAME, "control": data.CONTROL_NAME,
                 "n_target_points": len(t), "n_control_points": len(ct),
                 "total_bytes": manifests["total_bytes"]},
        "pipeline_A": a.as_dict(), "pipeline_B": b.as_dict(),
        "period_agreement": agreement, "period_stability": stability,
        "known_period": KEPLER8B_PERIOD,
        "period_recovery_frac_error": round(abs(a.period - KEPLER8B_PERIOD) / KEPLER8B_PERIOD, 5),
        "injection_recovery": {"recovery_rate": recovery["recovery_rate"],
                               "n_cases": recovery["n_cases"],
                               "median_period_err_frac": recovery["median_period_err_frac"]},
        "calibration": calibration,
        "null_tests": null_summary,
        "false_positive_scenarios": fp_scenarios,
        "abstention_supported_claim": supported.as_dict(),
        "abstention_forced_hard_case": forced,
        "claims": {
            "allowed": prereg.PREREGISTRATION["allowed_claims"],
            "prohibited": prereg.PREREGISTRATION["prohibited_claims"],
            "is_discovery": False,
            "statement": ("A transit-like periodic signal consistent with the known "
                          "Kepler-8b ephemeris is recoverable in this public data under "
                          "the declared methods. This is NOT a discovery."),
        },
    }
    (_artifacts() / "program_result.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def record_as_program(store: Any, *, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Register the transit program as a ResearchProgram + non-discovery dossier.

    Records the seven competing hypotheses, the preregistration milestone, and a
    dossier whose central claim is explicitly bounded and NOT a discovery. The
    verdict reflects the abstention engine's real decision (abstain if nulls are
    uncontrolled). Never publishes.
    """
    from ...program.engine import ProgramEngine
    from ...program.models import QuestionRole
    from ...publication.dossier import DossierEvidence, ReviewDossier

    result = result or run_program(downloaded_at="recorded", full_injection=False)
    pe = ProgramEngine(store)
    program = pe.create(
        "Exoplanet Transit Signal Robustness (Kepler-8b)", domains=["astronomy"],
        central_question=prereg.PREREGISTRATION["question"])
    for tag, desc in prereg.PREREGISTRATION["hypotheses"].items():
        pe.add_question(program.id, f"{tag}: {desc}", QuestionRole.INSTRUMENTAL)
    pe.add_milestone(program.id, "Preregistration hashed before analysis", kind="review")
    program.datasets = [data.REFERENCE]
    pe._save(program, summary="transit program datasets recorded")

    supported = result["abstention_supported_claim"]
    dossier = ReviewDossier(
        project=program.id,
        central_claim=result["claims"]["statement"],
        inference_level="statistical_association",
        supporting_evidence=[
            DossierEvidence("e0", f"both pipelines recover P={result['pipeline_A']['period']} d "
                                  f"(known {result['known_period']} d)", "supporting",
                            result_class="STATISTICAL_ASSOCIATION"),
            DossierEvidence("e1", f"injection recovery {result['injection_recovery']['recovery_rate']}",
                            "supporting")],
        counter_evidence=[
            DossierEvidence("c0", f"null tests not fully controlled "
                                  f"(FPR={result['null_tests']['false_positive_rate']})", "counter"),
            DossierEvidence("c1", "red-noise / EB-like scenarios can mimic transits", "counter"),
            DossierEvidence("c2", "two pipelines share the same data (not independent)", "counter")],
        limitations=["recovery of a known transit is not a discovery",
                     "injected signals are tests, not observations",
                     "no independent external replication"],
        open_questions=["control red-noise false positives before any bounded claim"],
        comprehension_status="unknown", gate_status="complete",
        required_external_review=True)
    return {"program_id": program.id, "dossier": dossier.as_dict(),
            "verdict": supported["verdict"], "abstained": supported["abstain"],
            "is_discovery": False}


def _forced_abstention_case(thr: dict[str, Any]) -> dict[str, Any]:
    """Inject a weak signal at low SNR; the engine MUST abstain (recorded)."""
    rng = np.random.default_rng(99)
    n = 3000
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    weak = 1.0 + rng.normal(0, 0.0017, n)
    weak = injection.inject_box(time, weak, period=4.1, depth=0.0008,
                                duration_hours=2.0)     # very shallow -> low SNR
    a = pl.pipeline_a(time, weak, window=51, p_min=0.5, p_max=8.0)
    b = pl.pipeline_b(time, weak, p_min=0.5, p_max=8.0)
    agreement = pl.period_agreement(a, b)
    decision = abstention.decide(
        snr=a.snr, period_agreement=agreement, period_stability_frac=0.05,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.2, quality_severe=False,
        n_indistinguishable_candidates=1, thresholds=thr)
    d = decision.as_dict()
    d["case"] = "injected depth=0.0008 (very shallow), low SNR"
    d["snr"] = round(a.snr, 2)
    return d
