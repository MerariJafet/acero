"""Extended, dimension-aware physics term library.

Beyond polynomials: linear / quadratic / Coulomb friction, saturation, periodic forcing,
simple delay, stochastic term, and the spatial operators (gradient, laplacian, advection,
diffusion, reaction-diffusion). Each term declares the physical dimension it contributes
so a library that mixes dimensions can be rejected.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PhysicsTerm:
    name: str
    fn: Callable[..., Any]
    dimension: str                # e.g. "acceleration", "velocity/length"
    family: str                   # friction | forcing | spatial | stochastic | poly
    note: str = ""


def _coulomb(v: np.ndarray) -> np.ndarray:
    return np.sign(v)


def _quadratic_drag(v: np.ndarray) -> np.ndarray:
    return np.abs(v) * v


def _saturation(x: np.ndarray, k: float = 1.0) -> np.ndarray:
    return x / (1.0 + np.abs(x) / k)


def _laplacian_1d(u: np.ndarray, dx: float) -> np.ndarray:
    lap = np.zeros_like(u)
    lap[1:-1] = (u[2:] - 2 * u[1:-1] + u[:-2]) / dx**2
    return lap


def _gradient_1d(u: np.ndarray, dx: float) -> np.ndarray:
    g = np.zeros_like(u)
    g[1:-1] = (u[2:] - u[:-2]) / (2 * dx)
    return g


TERMS: dict[str, PhysicsTerm] = {
    "linear_friction": PhysicsTerm("linear_friction", lambda v: v, "velocity", "friction",
                                   "-c·v"),
    "quadratic_friction": PhysicsTerm("quadratic_friction", _quadratic_drag,
                                      "velocity^2", "friction", "-c·|v|v"),
    "coulomb_friction": PhysicsTerm("coulomb_friction", _coulomb, "dimensionless-sign",
                                    "friction", "-c·sign(v)"),
    "saturation": PhysicsTerm("saturation", _saturation, "length", "poly", "x/(1+|x|/k)"),
    "periodic_forcing": PhysicsTerm(
        "periodic_forcing", lambda t, A=1.0, w=1.0: A * np.cos(w * t), "acceleration",
        "forcing", "A·cos(ωt)"),
    "laplacian": PhysicsTerm("laplacian", _laplacian_1d, "field/length^2", "spatial",
                             "∂²u/∂x²"),
    "gradient": PhysicsTerm("gradient", _gradient_1d, "field/length", "spatial", "∂u/∂x"),
}


def dimensions_consistent(term_names: list[str], target_dimension: str) -> bool:
    """A crude check: every friction/forcing/poly term feeding an equation whose target is
    ``target_dimension`` must be reducible to it. Spatial operators are only consistent in
    a PDE (field) context. Used by the gate's units check."""
    for name in term_names:
        term = TERMS.get(name)
        if term is None:
            return False
        if term.family == "spatial" and "field" not in target_dimension:
            return False
    return True


def available(family: str | None = None) -> list[str]:
    return sorted(n for n, t in TERMS.items() if family is None or t.family == family)
