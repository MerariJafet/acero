"""Governing Structure Inference Engine — orchestrator (Sprints 8.8–8.9).

Runs the pipeline: derivatives → library → sparse identification (+ stability) →
invariants → regimes → identifiability → abstention. Reports what was INFERRED vs
IMPOSED and the honest inference LEVEL. Never calls a fitted equation a law.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .data.derivatives import estimate
from .data.observations import Observations
from .discovery import change_points, invariants
from .discovery.sparse_identification import identify, stability_selection, threshold_sensitivity
from .libraries.terms import TermLibrary
from .model_selection.identifiability import assess
from .models import InferenceLevel, StructureInferenceProblem


def assess_variable_relevance(obs: Observations) -> list[dict[str, Any]]:
    out = []
    for v in obs.variables:
        y = obs.data[v]
        near_const = bool(np.std(y) < 1e-3 * (np.abs(np.mean(y)) + 1e-9))
        # redundancy: max abs correlation with the other variables
        red = 0.0
        for w in obs.variables:
            if w == v:
                continue
            c = float(abs(np.corrcoef(y, obs.data[w])[0, 1])) if np.std(obs.data[w]) > 0 else 0.0
            red = max(red, c)
        out.append({"variable": v, "near_constant": near_const,
                    "redundancy": round(red, 4), "note": "predictive != causal"})
    return out


class StructureInferenceEngine:
    def __init__(self, *, min_samples: int = 40) -> None:
        self.min_samples = min_samples

    def infer(self, problem: StructureInferenceProblem, obs: Observations, *,
              derivative_method: str = "auto", threshold: float = 0.2,
              families: set[str] | None = None, max_complexity: int = 2,
              stability: bool = True) -> dict[str, Any]:
        families = families or {"poly", "interaction"}
        lib = TermLibrary.build(obs.variables, obs.data, families=families,
                                max_complexity=max_complexity,
                                forbidden=problem.forbidden_terms)
        theta, names = lib.theta(obs.data)

        equations: dict[str, Any] = {}
        identifiabilities: dict[str, str] = {}
        for target in problem.variables_observed or obs.variables:
            d = estimate(obs.t, obs.data[target], method=derivative_method)
            eq = identify(theta, names, d.dydt, f"d{target}/dt", threshold=threshold)
            stab = stability_selection(theta, names, d.dydt) if stability else {}
            sens = threshold_sensitivity(theta, names, d.dydt)
            active_idx = [names.index(t) for t in eq.active_terms] if eq.active_terms else []
            ident = assess(theta[:, active_idx]) if active_idx else assess(theta[:, :1])
            identifiabilities[target] = ident.status.value
            equations[f"d{target}/dt"] = {
                "expression": eq.expression(), "coefficients": eq.coefficients,
                "r2": eq.r2, "rmse": eq.rmse,
                "derivative_method": d.method, "derivative_error": d.estimated_error,
                "unreliable_index": d.unreliable_index[:8],
                "term_stability": stab, "threshold_sensitivity": sens,
                "identifiability": ident.status.value,
                "condition_number": ident.condition_number,
            }

        invs = invariants.find_invariants(theta, names, top_k=2)
        # Use the first observed variable for change-point detection (representative).
        rep = (problem.variables_observed or obs.variables)[0]
        regimes = change_points.detect_change_points(obs.t, obs.data[rep], theta, names)

        abstention = self._abstain(obs, equations, identifiabilities, invs, regimes)
        level = self._level(equations, abstention)
        return {
            "problem_id": problem.id, "phenomenon": problem.phenomenon,
            "n_samples": obs.n(), "variables": obs.variables,
            "variable_relevance": assess_variable_relevance(obs),
            "library": {"terms": names, "excluded": lib.excluded[:10],
                        "families": sorted(families), "max_complexity": max_complexity},
            "equations": equations,
            "invariants": [{"expression": c.expression, "classification": c.classification,
                            "relative_variation": c.relative_variation} for c in invs],
            "regimes": regimes,
            "identifiability": identifiabilities,
            "inference_level": level.value,
            "imposed": [f"library families {sorted(families)}",
                        f"max complexity {max_complexity}",
                        "polynomial ODE ansatz", f"forbidden terms {problem.forbidden_terms}",
                        f"derivative estimation: {derivative_method}"],
            "inferred": [equations[k]["expression"] for k in equations],
            "abstention": abstention,
            "coefficient_note": ("Coefficients are point estimates without calibrated "
                                 "uncertainty; do not read their precision as confidence."),
            "honesty": [
                "El sistema identifica estructura DESDE una biblioteca IMPUESTA; no la descubre de la nada.",
                "Una ecuación recuperada por ajuste NO es una ley.",
                "Los coeficientes reflejan estos datos y esta biblioteca, no un mecanismo verdadero.",
                "Las derivadas se estiman de los MISMOS datos usados en la regresión "
                "(limitación intrínseca de SINDy); un R² alto puede ser interpolación.",
                "La biblioteca es polinómica; dinámicas no polinómicas (fricción de Coulomb, "
                "saturaciones, etc.) no pueden recuperarse sin ampliarla.",
                "Los coeficientes se reportan sin intervalos de confianza calibrados.",
            ],
        }

    def _abstain(self, obs, equations, identifiabilities, invs, regimes) -> dict[str, Any]:
        reasons = []
        if obs.n() < self.min_samples:
            reasons.append("insufficient data to estimate derivatives reliably")
        if any(v == "NON_IDENTIFIABLE" for v in identifiabilities.values()):
            reasons.append("structure is not identifiable (parameters correlated)")
        if any(v == "DATA_INSUFFICIENT" for v in identifiabilities.values()):
            reasons.append("data insufficient for the number of active terms")
        low_r2 = [k for k, e in equations.items() if e["r2"] < 0.5]
        if low_r2:
            reasons.append(f"derivative fit unreliable for {low_r2} (noisy derivatives?)")
        if regimes.get("regime_change"):
            reasons.append("a single global equation is misleading (regime change detected)")
        return {"abstains": bool(reasons), "reasons": reasons,
                "statement": "no lo sé con los datos actuales" if reasons else
                "estructura identificada dentro de la biblioteca impuesta"}

    def _level(self, equations, abstention) -> InferenceLevel:
        if abstention["abstains"]:
            return InferenceLevel.CURVE_FITTING
        good = all(e["r2"] > 0.8 for e in equations.values()) if equations else False
        return (InferenceLevel.SYSTEM_IDENTIFICATION if good
                else InferenceLevel.CURVE_FITTING)
