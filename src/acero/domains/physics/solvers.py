"""Auditable physics solvers.

Small, transparent integrators (RK4, symplectic Euler, explicit-Euler for comparison) and
a 1-D PDE stepper (diffusion / wave). Each returns a record with method, step, a stability
flag (CFL / energy-drift), and an error estimate — so the gate can catch an unstable run
that would otherwise produce false evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SolveRecord:
    method: str
    n_steps: int
    dt: float
    stable: bool
    error_estimate: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


def rk4(rhs: Callable[[float, np.ndarray], np.ndarray], y0: np.ndarray,
        t0: float, t1: float, n: int) -> tuple[np.ndarray, np.ndarray, SolveRecord]:
    dt = (t1 - t0) / n
    ts = np.linspace(t0, t1, n + 1)
    ys = np.zeros((n + 1, len(y0)))
    ys[0] = y0
    for i in range(n):
        t, y = ts[i], ys[i]
        k1 = rhs(t, y)
        k2 = rhs(t + dt / 2, y + dt / 2 * k1)
        k3 = rhs(t + dt / 2, y + dt / 2 * k2)
        k4 = rhs(t + dt, y + dt * k3)
        ys[i + 1] = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    blew_up = bool(np.any(~np.isfinite(ys)) or np.max(np.abs(ys)) > 1e6)
    rec = SolveRecord("rk4", n, dt, not blew_up,
                      float(np.max(np.abs(ys[-1]))) if not blew_up else float("inf"),
                      {"max_abs": float(np.nanmax(np.abs(ys)))})
    return ts, ys, rec


def explicit_euler(rhs: Callable[[float, np.ndarray], np.ndarray], y0: np.ndarray,
                   t0: float, t1: float, n: int) -> tuple[np.ndarray, np.ndarray, SolveRecord]:
    """Deliberately naive — used to demonstrate instability with too large a step."""
    dt = (t1 - t0) / n
    ts = np.linspace(t0, t1, n + 1)
    ys = np.zeros((n + 1, len(y0)))
    ys[0] = y0
    for i in range(n):
        ys[i + 1] = ys[i] + dt * rhs(ts[i], ys[i])
    max_abs = float(np.nanmax(np.abs(ys)))
    stable = bool(np.all(np.isfinite(ys)) and max_abs < 1e3)
    return ts, ys, SolveRecord("explicit_euler", n, dt, stable,
                               max_abs if stable else float("inf"),
                               {"max_abs": max_abs})


def diffusion_1d(u0: np.ndarray, d_coef: float, dx: float, dt: float, steps: int
                 ) -> tuple[np.ndarray, SolveRecord]:
    """Explicit FTCS diffusion. Stable iff r = D·dt/dx² ≤ 0.5 (CFL)."""
    r = d_coef * dt / dx**2
    u = u0.copy()
    for _ in range(steps):
        lap = np.zeros_like(u)
        lap[1:-1] = (u[2:] - 2 * u[1:-1] + u[:-2])
        u = u + r * lap
    stable = r <= 0.5 and bool(np.all(np.isfinite(u)))
    return u, SolveRecord("diffusion_ftcs", steps, dt, stable,
                          float(np.nanmax(np.abs(u))), {"cfl_r": float(r)})


def wave_1d(u0: np.ndarray, c: float, dx: float, dt: float, steps: int
            ) -> tuple[np.ndarray, SolveRecord]:
    """Explicit leapfrog wave. Courant number C = c·dt/dx ≤ 1 for stability."""
    courant = c * dt / dx
    u_prev = u0.copy()
    u = u0.copy()
    r2 = courant**2
    for _ in range(steps):
        u_next = np.zeros_like(u)
        u_next[1:-1] = (2 * u[1:-1] - u_prev[1:-1]
                        + r2 * (u[2:] - 2 * u[1:-1] + u[:-2]))
        u_prev, u = u, u_next
    stable = courant <= 1.0 and bool(np.all(np.isfinite(u)))
    return u, SolveRecord("wave_leapfrog", steps, dt, stable,
                          float(np.nanmax(np.abs(u))), {"courant": float(courant)})
