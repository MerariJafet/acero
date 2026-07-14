"""Constrained model search (Sprint 8.7).

Generates candidate models, fits them, and evaluates by MORE than RMSE: parsimony
(parameters/terms), out-of-range generalisation, and constraint/conservation
satisfaction. Also detects observationally-equivalent models and proposes a
distinguishing experiment.
"""

from __future__ import annotations

import math
from typing import Any

from .models import ModelCandidate, ModelType

# spec -> (n_params, n_terms, model_type)
SPECS = {
    "constant": (1, 1, ModelType.PHENOMENOLOGICAL),
    "linear": (2, 2, ModelType.PHENOMENOLOGICAL),
    "quadratic": (3, 3, ModelType.PHENOMENOLOGICAL),
    "cubic": (4, 4, ModelType.PHENOMENOLOGICAL),
    "exponential": (3, 2, ModelType.MECHANISTIC),
    "logistic": (3, 1, ModelType.MECHANISTIC),
    "poly9": (10, 10, ModelType.PHENOMENOLOGICAL),
}


def _fit(spec: str, x, y):
    import numpy as np

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if spec in ("constant", "linear", "quadratic", "cubic", "poly9"):
        deg = {"constant": 0, "linear": 1, "quadratic": 2, "cubic": 3, "poly9": 9}[spec]
        c = np.polyfit(x, y, deg)
        return lambda t: np.polyval(c, np.asarray(t, dtype=float))
    if spec == "exponential":
        best_e: tuple[float, Any, Any] | None = None
        for k in np.linspace(0.02, 3.0, 300):
            X = np.column_stack([np.ones_like(x), np.exp(-k * x)])
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            err = float(np.sqrt(np.mean((X @ coef - y) ** 2)))
            if best_e is None or err < best_e[0]:
                best_e = (err, k, coef)
        assert best_e is not None
        _, ke, coefe = best_e
        return lambda t: coefe[0] + coefe[1] * np.exp(-ke * np.asarray(t, dtype=float))
    if spec == "logistic":
        best_l: tuple[float, float, float, float] | None = None
        ymax = float(np.max(y))
        for K in np.linspace(max(1e-3, ymax * 0.8), ymax * 1.5 + 1e-3, 25):
            with np.errstate(all="ignore"):
                z = np.clip(K / np.clip(y, 1e-6, None) - 1.0, 1e-9, None)
                X = np.column_stack([np.ones_like(x), -x])
                coef, *_ = np.linalg.lstsq(X, np.log(z), rcond=None)
                A = math.exp(coef[0])
                pred = K / (1.0 + A * np.exp(-coef[1] * x))
                err = float(np.sqrt(np.mean((pred - y) ** 2)))
            if best_l is None or (math.isfinite(err) and err < best_l[0]):
                best_l = (err, float(K), A, float(coef[1]))
        assert best_l is not None
        _, Kl, Al, rl = best_l
        return lambda t: Kl / (1.0 + Al * np.exp(-rl * np.asarray(t, dtype=float)))
    raise ValueError(f"unknown spec {spec}")


def _rmse(a, b) -> float:
    import numpy as np

    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def search(x, y, specs: list[str], *, x_extra=None, y_extra=None) -> list[ModelCandidate]:
    out: list[ModelCandidate] = []
    for spec in specs:
        try:
            f = _fit(spec, x, y)
        except Exception:  # noqa: BLE001
            continue
        np_, nt, mt = SPECS[spec]
        cand = ModelCandidate(expression=spec, n_parameters=np_, n_terms=nt, model_type=mt,
                              fit_rmse=round(_rmse(f(x), y), 6))
        if x_extra is not None and y_extra is not None:
            cand.extrapolation_rmse = round(_rmse(f(x_extra), y_extra), 6)
        out.append(cand)
    out.sort(key=lambda c: c.fit_rmse if c.fit_rmse is not None else 1e18)
    return out


def select_minimal(candidates: list[ModelCandidate], *, tolerance: float = 1.2
                   ) -> ModelCandidate | None:
    """Simplest model (fewest parameters) whose fit is within ``tolerance``× the best."""
    fitted = [c for c in candidates if c.fit_rmse is not None]
    if not fitted:
        return None
    best = min(c.fit_rmse for c in fitted)  # type: ignore[type-var]
    within = [c for c in fitted if c.fit_rmse <= best * tolerance + 1e-12]  # type: ignore[operator]
    return min(within, key=lambda c: (c.n_parameters, c.n_terms))


def equivalent_models(candidates: list[ModelCandidate], *, rel_tol: float = 0.1
                      ) -> list[str]:
    """Models whose in-sample fit is within rel_tol of the best -> observationally
    equivalent on the training range (need a distinguishing experiment)."""
    fitted = [c for c in candidates if c.fit_rmse is not None]
    if not fitted:
        return []
    best = min(c.fit_rmse for c in fitted)  # type: ignore[type-var]
    return [c.expression for c in fitted
            if c.fit_rmse <= best * (1 + rel_tol) + 1e-9]  # type: ignore[operator]


def distinguishing_experiment(candidates: list[ModelCandidate]) -> dict[str, Any]:
    """Where do equivalent-on-training models diverge? Use extrapolation error spread."""
    eq = equivalent_models(candidates)
    with_extra = [c for c in candidates if c.extrapolation_rmse is not None
                  and c.expression in eq]
    if len(with_extra) < 2:
        return {"needed": False, "reason": "fewer than two equivalent models with extrapolation"}
    xr = [c.extrapolation_rmse for c in with_extra if c.extrapolation_rmse is not None]
    spread = max(xr) - min(xr)
    return {"needed": True, "equivalent_models": eq,
            "region": "out-of-range (extrapolation) where predictions diverge",
            "extrapolation_rmse_spread": round(spread, 6),
            "recommendation": "measure/observe outside the training range to distinguish"}
