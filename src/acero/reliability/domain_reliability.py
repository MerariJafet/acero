"""Per-domain reliability checks (Sprint 11).

Refinement-convergence, stability, units, causality, multiple-testing, gaps/aliasing,
stiffness and extrapolation checks layered over the Sprint-10 labs.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..domains.physics import solvers


def physics_reliability() -> dict[str, Any]:
    """Refinement convergence: RK4 error on a known solution shrinks with more steps."""
    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        return np.array([y[1], -y[0]])            # x'' = -x, x(0)=1 → cos(t)
    errs = []
    for n in (100, 400, 1600):
        ts, ys, _ = solvers.rk4(rhs, np.array([1.0, 0.0]), 0, 6.0, n)
        errs.append(float(np.max(np.abs(ys[:, 0] - np.cos(ts)))))
    converges = errs[0] > errs[1] > errs[2]
    order = float(np.log2(errs[0] / errs[1])) if errs[1] > 0 else 0.0
    # stable vs unstable step
    _, _, stable = solvers.rk4(lambda t, y: np.array([y[1], -y[0]]),
                               np.array([1.0, 0.0]), 0, 10, 2000)
    _, _, unstable = solvers.explicit_euler(lambda t, y: np.array([y[1], -100.0 * y[0]]),
                                            np.array([1.0, 0.0]), 0, 10, 40)
    return {"errors": [round(e, 6) for e in errs], "converges": converges,
            "empirical_order": round(order, 2),
            "detects_instability": stable.stable and not unstable.stable,
            "passed": converges and stable.stable and not unstable.stable}


def astronomy_reliability() -> dict[str, Any]:
    """Red-noise vs true signal: a random walk should not yield a confident period."""
    from ..domains.astronomy import time_series as ts
    rng = np.random.default_rng(0)
    t = np.linspace(0, 100, 500)
    red = np.cumsum(rng.standard_normal(len(t))) * 0.1
    _, red_power = ts.lomb_scargle_period(t, red, 1, 50)
    signal = np.sin(2 * np.pi * t / 5.0)
    _, sig_power = ts.lomb_scargle_period(t, signal, 1, 20)
    return {"red_noise_power": round(red_power, 3), "signal_power": round(sig_power, 3),
            "flags_red_noise": ts.false_alarm_low(red_power),
            "signal_stronger_than_noise": sig_power > red_power,
            "passed": sig_power > red_power}


def genetics_reliability() -> dict[str, Any]:
    """Multiple-testing + population structure: false positives controlled."""
    from ..domains.genetics.lab import GeneticsLab
    b = GeneticsLab().benchmark()
    return {"multiple_testing_controlled": b["4_diff_expression_multiple_testing"]["passed"],
            "population_structure_handled": b["3_population_structure_confound"]["passed"],
            "passed": (b["4_diff_expression_multiple_testing"]["passed"]
                       and b["3_population_structure_confound"]["passed"])}


def chemistry_reliability() -> dict[str, Any]:
    """Mass conservation + stiffness detection + non-identifiability."""
    from ..domains.chemistry.lab import ChemistryLab
    b = ChemistryLab().benchmark()
    return {"mass_conserved": b["5_mass_conservation"]["passed"],
            "stiffness_detected": b["6_stiff_system"]["passed"],
            "nonidentifiability_detected": not b["7_nonidentifiable_parameter"]["identifiable"],
            "passed": (b["5_mass_conservation"]["passed"] and b["6_stiff_system"]["passed"])}


def run_domain_reliability() -> dict[str, Any]:
    return {"physics": physics_reliability(), "astronomy": astronomy_reliability(),
            "genetics": genetics_reliability(), "chemistry": chemistry_reliability()}
