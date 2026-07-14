"""Identifiability assessment (Sprint 8.9).

Structural + practical identifiability from the active library: condition number
(parameter correlation), data sufficiency, and rank. Never present non-identifiable
parameters with false precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..models import IdentifiabilityStatus


@dataclass
class IdentifiabilityReport:
    status: IdentifiabilityStatus
    condition_number: float
    n_samples: int
    n_parameters: int
    max_parameter_correlation: float
    details: dict[str, Any] = field(default_factory=dict)


def assess(theta_active: np.ndarray, *, n_samples: int | None = None) -> IdentifiabilityReport:
    n = n_samples if n_samples is not None else theta_active.shape[0]
    p = theta_active.shape[1]
    if p == 0:
        return IdentifiabilityReport(IdentifiabilityStatus.NON_IDENTIFIABLE, float("inf"),
                                     n, 0, 1.0, {"reason": "no active terms"})
    # Condition number of the (normalised) design matrix.
    scales = np.linalg.norm(theta_active, axis=0)
    scales[scales == 0] = 1.0
    tn = theta_active / scales
    cond = float(np.linalg.cond(tn))
    # Parameter correlation from the covariance of (Θ'Θ)^-1.
    try:
        gram = tn.T @ tn
        cov = np.linalg.inv(gram)
        dinv = np.sqrt(np.diag(cov))
        corr = cov / np.outer(dinv, dinv)
        max_corr = float(np.max(np.abs(corr - np.eye(p)))) if p > 1 else 0.0
    except np.linalg.LinAlgError:
        max_corr = 1.0

    if n < p:
        status = IdentifiabilityStatus.DATA_INSUFFICIENT
    elif cond > 1e8 or max_corr > 0.999:
        status = IdentifiabilityStatus.NON_IDENTIFIABLE
    elif cond > 1e3 or max_corr > 0.95 or n < 3 * p:
        status = IdentifiabilityStatus.PARTIALLY_IDENTIFIABLE
    else:
        status = IdentifiabilityStatus.IDENTIFIABLE
    return IdentifiabilityReport(status, round(cond, 2), n, p, round(max_corr, 4),
                                 {"samples_per_parameter": round(n / p, 2)})
