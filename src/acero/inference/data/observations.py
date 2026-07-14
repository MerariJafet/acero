"""Observation containers and synthetic benchmark generators.

The generators integrate a HIDDEN governing ODE (RK4) and return only the data,
variable names, and (optionally) noise — never the equation. Used by the Governing
Dynamics Inference Benchmark.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Observations:
    t: np.ndarray
    data: dict[str, np.ndarray]           # variable name -> series
    units: dict[str, str] = field(default_factory=dict)
    dimensions: dict[str, str] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def variables(self) -> list[str]:
        return list(self.data)

    def matrix(self, variables: list[str] | None = None) -> np.ndarray:
        vs = variables or self.variables
        return np.column_stack([self.data[v] for v in vs])

    def n(self) -> int:
        return len(self.t)


# --- hidden governing systems (true ODEs; NOT given to the inference engine) ---
def _rhs(system: str) -> tuple[Callable[[np.ndarray], np.ndarray], list[str], dict[str, float]]:
    if system == "exponential_decay":
        return (lambda s: np.array([-0.7 * s[0]])), ["x"], {"x": 90.0}
    if system == "logistic":
        r, K = 0.8, 10.0
        return (lambda s: np.array([r * s[0] * (1 - s[0] / K)])), ["x"], {"x": 0.5}
    if system == "harmonic":
        w2 = 4.0
        return (lambda s: np.array([s[1], -w2 * s[0]])), ["x", "v"], {"x": 1.0, "v": 0.0}
    if system == "damped":
        w2, g = 4.0, 0.5
        return (lambda s: np.array([s[1], -w2 * s[0] - g * s[1]])), ["x", "v"], {"x": 1.0, "v": 0.0}
    if system == "predator_prey":
        a, b, c, d = 1.1, 0.4, 0.4, 0.1
        return (lambda s: np.array([a * s[0] - b * s[0] * s[1],
                                    -c * s[1] + d * s[0] * s[1]])), ["x", "y"], {"x": 10.0, "y": 5.0}
    raise ValueError(f"unknown system {system}")


def _integrate(f, s0: np.ndarray, t: np.ndarray) -> np.ndarray:
    out = np.zeros((len(t), len(s0)))
    s = s0.astype(float).copy()
    out[0] = s
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        k1 = f(s)
        k2 = f(s + 0.5 * dt * k1)
        k3 = f(s + 0.5 * dt * k2)
        k4 = f(s + dt * k3)
        s = s + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        out[i] = s
    return out


def generate(system: str, *, seed: int = 0, n: int = 300, t_max: float = 6.0,
             noise: float = 0.0, noise_kind: str = "gaussian",
             irregular: bool = False, missing_fraction: float = 0.0) -> Observations:
    rng = np.random.default_rng(seed)
    f, names, ic = _rhs(system)
    if irregular:
        t = np.sort(rng.uniform(0, t_max, size=n))
        t[0] = 0.0
    else:
        t = np.linspace(0, t_max, n)
    traj = _integrate(f, np.array([ic[k] for k in names]), t)

    data: dict[str, np.ndarray] = {}
    for j, name in enumerate(names):
        y = traj[:, j].copy()
        if noise > 0:
            if noise_kind == "correlated":
                e = rng.normal(0, noise, size=len(t))
                y = y + np.cumsum(e) / np.sqrt(np.arange(1, len(t) + 1))  # colored-ish
            else:
                y = y + rng.normal(0, noise, size=len(t))
        data[name] = y

    if missing_fraction > 0:
        k = int(missing_fraction * n)
        drop = rng.choice(np.arange(10, n - 10), size=k, replace=False)
        keep = np.array([i for i in range(n) if i not in set(drop)])
        t = t[keep]
        data = {name: y[keep] for name, y in data.items()}

    return Observations(t=t, data=data,
                        units={name: "" for name in names},
                        dimensions={name: "dimensionless" for name in names},
                        meta={"system": system, "seed": seed, "noise": noise,
                              "noise_kind": noise_kind, "irregular": irregular,
                              "missing_fraction": missing_fraction})
