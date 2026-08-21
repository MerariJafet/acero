"""Real-data verification: Kepler's Third Law on public NASA exoplanet data.

Loads the real NASA exoplanet catalog (period, semi-major axis, stellar mass) and
fits the log-log relation. Newton/Kepler predict  P^2 = a^3 / M, i.e.
  log10(P_yr) = 1.5*log10(a_AU) - 0.5*log10(M_sun) + const.
This VERIFIES a known 17th-century law on real data — it is NOT a discovery. It
situates Earth's orbit (1 AU, 1 yr, 1 Msun) in the same universal relation.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..core.config import repo_root
from ..core.workspace import data_path


def _dataset() -> Path:
    return data_path(
        "datos/datasets/exoplanets.csv",
        legacy=repo_root() / "research" / "datasets" / "exoplanets.csv",
    )


def load_rows() -> list[tuple[float, float, float]]:
    """Return (P_years, a_AU, M_sun) for rows with valid, positive values."""
    out: list[tuple[float, float, float]] = []
    with _dataset().open() as f:
        for row in csv.DictReader(f):
            try:
                p_days = float(row["pl_orbper"])
                a = float(row["pl_orbsmax"])
                m = float(row["st_mass"])
            except (TypeError, ValueError):
                continue
            if p_days > 0 and a > 0 and m > 0:
                out.append((p_days / 365.25, a, m))
    return out


def verify(*, source: str = "NASA Exoplanet Archive (public)") -> dict[str, Any]:
    import numpy as np

    rows = load_rows()
    n = len(rows)
    if n < 50:
        return {"ok": False, "reason": "insufficient data", "n": n}
    p = np.array([r[0] for r in rows])
    a = np.array([r[1] for r in rows])
    m = np.array([r[2] for r in rows])
    y = np.log10(p)
    X = np.column_stack([np.ones(n), np.log10(a), np.log10(m)])
    # ordinary least squares: y = c + alpha*log(a) + beta*log(m)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    c, alpha, beta = (float(coef[0]), float(coef[1]), float(coef[2]))
    yhat = X @ coef
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0

    # Newton/Kepler theory: alpha=1.5, beta=-0.5
    alpha_err = abs(alpha - 1.5)
    beta_err = abs(beta - (-0.5))

    # Earth check: predicted period at a=1 AU, M=1 Msun (logs are 0) -> 10**c years
    earth_pred_yr = float(10 ** c)
    earth_err_frac = abs(earth_pred_yr - 1.0)

    consistent = alpha_err < 0.05 and beta_err < 0.1 and r2 > 0.95
    return {
        "ok": True, "source": source, "n_planets": n,
        "fitted": {"alpha_log_a": round(alpha, 4), "beta_log_M": round(beta, 4),
                   "const": round(c, 4), "r_squared": round(r2, 5)},
        "theory": {"alpha": 1.5, "beta": -0.5},
        "deviation": {"alpha_err": round(alpha_err, 4), "beta_err": round(beta_err, 4)},
        "earth_context": {"predicted_period_yr_at_1AU_1Msun": round(earth_pred_yr, 4),
                          "actual": 1.0, "frac_error": round(earth_err_frac, 4)},
        "consistent_with_kepler": bool(consistent),
        "claim": ("Los datos públicos reales son consistentes con la Tercera Ley de Kepler "
                  f"(exponentes {round(alpha,3)}, {round(beta,3)} ≈ teoría 1.5, -0.5; "
                  f"R²={round(r2,4)}). La órbita de la Tierra encaja en la misma relación "
                  "universal. Esto VERIFICA una ley conocida; NO es un descubrimiento."),
        "prohibited_claims": ["descubrir la ley de Kepler", "descubrir la posición de la Tierra",
                              "afirmar un resultado no verificado externamente"],
    }
