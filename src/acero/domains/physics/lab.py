"""Physics Lab: contract, benchmarks, result classification."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.contracts import (
    Concept,
    DomainCapabilities,
    DomainLab,
    DomainModel,
    DomainResultClass,
    SafetyClass,
    ScientificDomain,
)
from . import solvers

_G = 9.81


class PhysicsLab(DomainLab):
    def domain(self) -> ScientificDomain:
        return ScientificDomain(
            id="physics", name="Classical & Computational Physics",
            ontology="mechanics, dynamical systems, oscillations, diffusion, waves, "
                     "thermodynamics, intro EM, complex systems",
            concepts=[
                Concept("oscillation", "periodic exchange of restoring force and inertia",
                        ["x", "v"], {"x": "m", "v": "m/s"}),
                Concept("diffusion", "spread down a concentration/temperature gradient",
                        ["u"], {"u": "field"}),
                Concept("wave", "propagating disturbance", ["u"], {"u": "field"}),
                Concept("conservation", "invariant of the motion (energy, momentum)", []),
            ],
            units={"length": "m", "time": "s", "mass": "kg", "energy": "J"},
            dimensions={"velocity": "L/T", "acceleration": "L/T^2", "force": "M·L/T^2"},
            scales={"micro": "molecular", "meso": "lab", "macro": "engineering"},
            supported_problem_types=["ODE", "PDE-1D", "eigenvalue", "monte-carlo",
                                     "optimization", "symbolic-check"],
            models=[
                DomainModel("damped_oscillator", "m x'' + c x' + k x = 0",
                            ["linear damping"], "small dissipation",
                            DomainResultClass.MODEL_FIT),
                DomainModel("diffusion", "u_t = D u_xx", ["constant D"], "Fourier regime",
                            DomainResultClass.SIMULATION),
                DomainModel("wave", "u_tt = c^2 u_xx", ["non-dispersive"], "linear",
                            DomainResultClass.SIMULATION),
            ],
            tools=["term_library", "rk4", "diffusion_ftcs", "wave_leapfrog"],
            solvers=["rk4", "explicit_euler", "diffusion_1d", "wave_1d"],
            datasets=["synthetic (hidden-ODE generators)"],
            validation_rules=["dimensional consistency", "CFL stability",
                              "energy drift bound"],
            gate_rule_ids=["domain.units_consistent", "domain.solver_stable",
                           "domain.simulation_not_physical_validation"],
            safety_class=SafetyClass.LOW,
            capabilities=DomainCapabilities(
                can_do=["integrate ODEs/PDE-1D", "check conservation & stability",
                        "fit dynamical models", "infer term structure (via inference engine)"],
                cannot_do=["high-energy physics", "3-D turbulent PDE", "lab measurement"],
                approximations=["1-D PDE", "explicit schemes", "small parameter regimes"],
                dependencies=["numpy"],
                risks=["unstable schemes can produce false evidence"],
                needs_collaboration=["any physical validation / experiment"]),
            learning_requirement_kind="sindy")

    def classify(self, kind: str) -> DomainResultClass:
        return {
            "integration": DomainResultClass.SIMULATION,
            "fit": DomainResultClass.MODEL_FIT,
            "period": DomainResultClass.CALCULATION,
            "conservation": DomainResultClass.CALCULATION,
        }.get(kind, DomainResultClass.SIMULATION)

    # --- benchmark ------------------------------------------------------
    def benchmark(self) -> dict[str, Any]:
        return {
            "1_nonlinear_friction": self._nonlinear_friction(),
            "2_pendulum_large_angle": self._pendulum_large_angle(),
            "3_diffusion_1d": self._diffusion(),
            "4_wave_1d": self._wave(),
            "5_reaction_diffusion": self._reaction_diffusion(),
            "6_conservation_drift": self._conservation_drift(),
            "7_forced_resonance": self._forced_resonance(),
            "8_unstable_solver_false_evidence": self._unstable_solver(),
        }

    def _nonlinear_friction(self) -> dict[str, Any]:
        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            x, v = y
            return np.array([v, -4.0 * x - 0.5 * np.abs(v) * v])
        _, ys, rec = solvers.rk4(rhs, np.array([1.0, 0.0]), 0, 12, 2000)
        energy = 0.5 * ys[:, 1] ** 2 + 2.0 * ys[:, 0] ** 2
        return {"stable": rec.stable, "energy_decreases": bool(energy[-1] < energy[0]),
                "passed": rec.stable and energy[-1] < energy[0]}

    def _pendulum_large_angle(self) -> dict[str, Any]:
        length = 1.0
        w0 = np.sqrt(_G / length)
        t0_small = 2 * np.pi / w0

        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            th, om = y
            return np.array([om, -(_G / length) * np.sin(th)])
        ts, ys, _ = solvers.rk4(rhs, np.array([2.0, 0.0]), 0, 6.0, 6000)  # ~115°
        # period from zero-crossing of angular velocity sign change (return to max)
        peaks = np.where(np.diff(np.sign(ys[:, 1])) > 0)[0]
        period = float(ts[peaks[1]] - ts[peaks[0]]) if len(peaks) >= 2 else t0_small
        return {"small_angle_period": round(t0_small, 4),
                "large_angle_period": round(period, 4),
                "passed": period > t0_small}     # large-angle period is LONGER

    def _diffusion(self) -> dict[str, Any]:
        nx = 201
        x = np.linspace(-5, 5, nx)
        dx = x[1] - x[0]
        u0 = np.exp(-x**2)
        var0 = float(np.sum(x**2 * u0) / np.sum(u0))
        u, rec = solvers.diffusion_1d(u0, d_coef=0.5, dx=dx, dt=0.4 * dx**2 / 0.5,
                                      steps=400)
        var1 = float(np.sum(x**2 * u) / np.sum(u))
        return {"stable": rec.stable, "cfl_r": rec.diagnostics["cfl_r"],
                "variance_grows": bool(var1 > var0),
                "passed": rec.stable and var1 > var0}

    def _wave(self) -> dict[str, Any]:
        nx = 201
        x = np.linspace(0, 10, nx)
        dx = x[1] - x[0]
        u0 = np.exp(-(x - 5)**2)
        u, rec = solvers.wave_1d(u0, c=1.0, dx=dx, dt=0.5 * dx, steps=200)
        return {"stable": rec.stable, "courant": rec.diagnostics["courant"],
                "bounded": bool(np.nanmax(np.abs(u)) < 5.0),
                "passed": rec.stable and np.nanmax(np.abs(u)) < 5.0}

    def _reaction_diffusion(self) -> dict[str, Any]:
        nx = 101
        u = np.random.default_rng(0).random(nx) * 0.1 + 0.5
        r = 0.4
        for _ in range(300):
            lap = np.zeros_like(u)
            lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
            u = u + r * lap + 0.01 * (u * (1 - u))       # logistic reaction
            u = np.clip(u, 0, 5)
        return {"bounded": bool(np.all(np.isfinite(u)) and u.max() < 5),
                "passed": bool(np.all(np.isfinite(u)) and u.max() < 5)}

    def _conservation_drift(self) -> dict[str, Any]:
        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            x, v = y
            return np.array([v, -4.0 * x])               # undamped → energy conserved
        _, ys, _ = solvers.rk4(rhs, np.array([1.0, 0.0]), 0, 20, 4000)
        e = 0.5 * ys[:, 1]**2 + 2.0 * ys[:, 0]**2
        drift = float(abs(e[-1] - e[0]) / e[0])
        return {"energy_drift": round(drift, 5), "passed": drift < 0.02}

    def _forced_resonance(self) -> dict[str, Any]:
        w0 = 2.0
        amps = {}
        for w in (1.0, 2.0, 3.0):
            def rhs(t: float, y: np.ndarray, w=w) -> np.ndarray:
                x, v = y
                return np.array([v, -w0**2 * x - 0.1 * v + np.cos(w * t)])
            _, ys, _ = solvers.rk4(rhs, np.array([0.0, 0.0]), 0, 80, 8000)
            amps[w] = float(np.max(np.abs(ys[-2000:, 0])))
        peak_at_resonance = amps[2.0] > amps[1.0] and amps[2.0] > amps[3.0]
        return {"amplitudes": {str(k): round(v, 3) for k, v in amps.items()},
                "peak_at_resonance": peak_at_resonance, "passed": peak_at_resonance}

    def _unstable_solver(self) -> dict[str, Any]:
        """Explicit Euler with too-large a step blows up: the solver flags it as unstable,
        so the gate can REJECT the (false) evidence."""
        def rhs(t: float, y: np.ndarray) -> np.ndarray:
            x, v = y
            return np.array([v, -100.0 * x])             # stiff-ish; big dt → unstable
        _, _, rec = solvers.explicit_euler(rhs, np.array([1.0, 0.0]), 0, 10, 60)
        # PASS means: the instability was DETECTED (stable is False) → gate will block.
        return {"solver_stable": rec.stable, "detected_instability": not rec.stable,
                "passed": not rec.stable}
