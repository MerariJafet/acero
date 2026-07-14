"""Discriminating experiment design (Sprint 8.9).

Given competing candidate models (ODE right-hand sides), find the initial condition /
region where their predictions diverge most, and propose the next measurement. The
DESIGN simulates known polynomial ODEs in-process; real experiment EXECUTION goes
through the sandbox (see benchmarks/governing_dynamics).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from pydantic import BaseModel, Field

from ..data.observations import _integrate


class DiscriminatingExperiment(BaseModel):
    competing_models: list[str] = Field(default_factory=list)
    proposed_intervention: str = ""
    initial_conditions: dict[str, float] = Field(default_factory=dict)
    variables_to_measure: list[str] = Field(default_factory=list)
    sampling_rate: float = 0.0
    predicted_divergence: float = 0.0
    expected_information_gain: float = 0.0
    cost: float = 0.0
    risk: float = 0.0
    assumptions: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)


def design(model_a: Callable[[np.ndarray], np.ndarray],
           model_b: Callable[[np.ndarray], np.ndarray],
           variables: list[str], *, candidate_ics: list[dict[str, float]],
           t_max: float = 6.0, n: int = 200, names: tuple[str, str] = ("A", "B")
           ) -> DiscriminatingExperiment:
    """Pick the initial condition that maximises trajectory divergence between models."""
    t = np.linspace(0, t_max, n)
    best_ic, best_div = None, -1.0
    for ic in candidate_ics:
        s0 = np.array([ic.get(v, 0.0) for v in variables], dtype=float)
        ta = _integrate(model_a, s0, t)
        tb = _integrate(model_b, s0, t)
        if not (np.all(np.isfinite(ta)) and np.all(np.isfinite(tb))):
            continue
        div = float(np.max(np.linalg.norm(ta - tb, axis=1)))
        if div > best_div:
            best_div, best_ic = div, ic
    if best_ic is None:
        return DiscriminatingExperiment(competing_models=list(names),
                                        failure_modes=["all candidate ICs diverged numerically"])
    # EIG heuristic: normalised divergence -> higher divergence, more discriminating.
    eig = float(np.tanh(best_div))
    return DiscriminatingExperiment(
        competing_models=list(names),
        proposed_intervention=f"set initial conditions to {best_ic} and observe {variables}",
        initial_conditions=best_ic, variables_to_measure=variables,
        sampling_rate=round(n / t_max, 2), predicted_divergence=round(best_div, 4),
        expected_information_gain=round(eig, 4), cost=0.3, risk=0.1,
        assumptions=["models integrable from this IC", "measurement noise moderate"],
        failure_modes=["divergence too small to measure under noise",
                       "IC not physically realisable"])
