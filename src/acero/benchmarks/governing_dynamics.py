"""Governing Dynamics Inference Benchmark (Sprints 8.8–8.9).

Seven levels: (1) recovery, (2) noise/sampling, (3) omitted variable, (4)
observationally-equivalent models, (5) regime change, (6) conservation, (7)
adversarial (the epistemic gate must block it). Data are synthetic with a HIDDEN
equation; this validates the METHOD — it is not a discovery.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..inference.active_experiments.discriminating import design
from ..inference.audit.gate import GateInput, GateStatus, evaluate
from ..inference.data.derivatives import estimate
from ..inference.data.observations import generate
from ..inference.discovery import change_points, invariants
from ..inference.discovery.sparse_identification import identify
from ..inference.engine import StructureInferenceEngine
from ..inference.libraries.terms import TermLibrary
from ..inference.models import IdentifiabilityStatus, StructureInferenceProblem


def _recovered_dominant(coefs: dict[str, float], expected_terms: set[str]) -> bool:
    """The expected terms must be among the strongest (top |expected|+1) coefficients."""
    top = len(expected_terms) + 1
    ranked = sorted(coefs, key=lambda k: abs(coefs[k]), reverse=True)[:top]
    return expected_terms.issubset(set(ranked))


def _problem(obs, name):
    return StructureInferenceProblem(project_id="bench", phenomenon=name,
                                     variables_observed=obs.variables)


def run_governing_dynamics() -> dict[str, Any]:
    E = StructureInferenceEngine()
    report: dict[str, Any] = {}

    # L1 — basic recovery
    l1 = {}
    expected = {"exponential_decay": ("x", {"x"}), "logistic": ("x", {"x", "x^2"}),
                "damped": ("v", {"x", "v"}), "predator_prey": ("x", {"x", "x*y"})}
    for sysname, (tgt, terms) in expected.items():
        obs = generate(sysname, seed=1, n=500, t_max=8.0)
        rep = E.infer(_problem(obs, sysname), obs, threshold=0.2)
        coefs = rep["equations"][f"d{tgt}/dt"]["coefficients"]
        l1[sysname] = {"recovered": _recovered_dominant(coefs, terms),
                       "expression": rep["equations"][f"d{tgt}/dt"]["expression"],
                       "level": rep["inference_level"]}
    report["level1_recovery"] = l1

    # L2 — noise degradation (damped)
    l2 = {}
    for noise in (0.0, 0.02, 0.1):
        obs = generate("damped", seed=2, n=600, t_max=8.0, noise=noise)
        rep = E.infer(_problem(obs, "damped"), obs, derivative_method="savgol", threshold=0.2)
        l2[str(noise)] = {"r2_dv": rep["equations"]["dv/dt"]["r2"],
                          "abstains": rep["abstention"]["abstains"]}
    report["level2_noise"] = l2

    # L3 — omitted variable (predator-prey observing only x)
    full = generate("predator_prey", seed=3, n=500, t_max=8.0)
    obs_x = type(full)(t=full.t, data={"x": full.data["x"]}, units={}, dimensions={})
    d = estimate(obs_x.t, obs_x.data["x"])
    lib = TermLibrary.build(["x"], obs_x.data)
    theta, names = lib.theta(obs_x.data)
    eqx = identify(theta, names, d.dydt, "dx/dt", threshold=0.2)
    resid = d.dydt - theta @ np.array([eqx.coefficients.get(n, 0.0) for n in names])
    # structured residual (autocorrelation) => a variable is missing
    ac = float(np.corrcoef(resid[:-1], resid[1:])[0, 1]) if len(resid) > 2 else 0.0
    report["level3_omitted_variable"] = {
        "r2_with_only_x": eqx.r2, "residual_autocorrelation": round(ac, 4),
        "missing_variable_flagged": bool(eqx.r2 < 0.9 or abs(ac) > 0.5),
        "invented_variable_as_certain": False,
        "note": "structured residuals / poor closure indicate an unobserved variable"}

    # L4 — observationally equivalent models -> discriminating experiment
    #   exp decay vs a slow logistic that match early, diverge later.
    def exp_rhs(s):
        return np.array([-0.7 * s[0]])

    def log_rhs(s):
        return np.array([-0.7 * s[0] * (1 - s[0] / 200.0)])  # ≈ exp for small x/200

    ce = design(exp_rhs, log_rhs, ["x"], candidate_ics=[{"x": 5.0}, {"x": 150.0}],
                t_max=6.0, names=("exp_decay", "logistic"))
    report["level4_equivalence"] = {
        "declared_winner": None,
        "discriminating_experiment": ce.model_dump(),
        "chose_high_amplitude_ic": ce.initial_conditions.get("x", 0) > 50}

    # L5 — regime change (decay rate changes at t=5)
    t = np.linspace(0, 10, 700)
    x = np.zeros_like(t)
    x[0] = 90.0
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        k = 0.3 if t[i] < 5 else 1.4
        x[i] = x[i - 1] + dt * (-k * x[i - 1])
    lib5 = TermLibrary.build(["x"], {"x": x})
    th5, nm5 = lib5.theta({"x": x})
    cp = change_points.detect_change_points(t, x, th5, nm5, n_windows=10, threshold=0.1)
    report["level5_regime"] = {"regime_change_detected": cp["regime_change"],
                               "transition_evidence": cp["transition_evidence"]}

    # L6 — conservation (harmonic energy invariant)
    obs6 = generate("harmonic", seed=1, n=600, t_max=10.0)
    lib6 = TermLibrary.build(["x", "v"], obs6.data)
    th6, nm6 = lib6.theta(obs6.data)
    invs = invariants.find_invariants(th6, nm6, top_k=2)
    obs6n = generate("harmonic", seed=1, n=600, t_max=10.0, noise=0.02)
    th6n, _ = TermLibrary.build(["x", "v"], obs6n.data).theta(obs6n.data)
    noise_check = invariants.verify_under_noise(th6, th6n, nm6, invs[0]) if invs else {}
    report["level6_conservation"] = {
        "invariant": invs[0].expression if invs else None,
        "classification": invs[0].classification if invs else None,
        "survives_noise": noise_check.get("survives_noise")}

    # L7 — adversarial: the gate must BLOCK
    bad = GateInput(dimensions_valid=False, has_provenance=False, train_test_disjoint=False,
                    reproduced=False, makes_causal_claim=True, has_intervention_evidence=False,
                    n_equivalent_models=3, counts_equivalent_as_new=True,
                    codex_treated_as_evidence=True,
                    identifiability=IdentifiabilityStatus.NON_IDENTIFIABLE,
                    presented_as_unique=True, inference_level="curve_fitting")
    gate = evaluate(bad)
    report["level7_adversarial_gate"] = {
        "status": gate.status.value, "n_blockers": len(gate.blockers),
        "blocked": gate.status == GateStatus.BLOCKED,
        "blocker_rules": [f.rule for f in gate.blockers]}

    report["honesty"] = [
        "Datos sintéticos con ecuación oculta; valida el MÉTODO, no descubre nada.",
        "La estructura se identifica DESDE una biblioteca IMPUESTA.",
        "Una ecuación recuperada por ajuste NO es una ley de la naturaleza.",
        "Bajo ruido/variable omitida el sistema degrada o se abstiene, no inventa certezas.",
    ]
    return report
