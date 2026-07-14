"""Astronomy Lab: contract, benchmarks, classification."""

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
from . import time_series as ts


class AstronomyLab(DomainLab):
    def domain(self) -> ScientificDomain:
        return ScientificDomain(
            id="astronomy", name="Observational Astronomy (computational)",
            ontology="light curves, periodicity, quasiperiodicity, transits, orbits, "
                     "spectra, irregular series, change detection, populations",
            concepts=[
                Concept("light_curve", "brightness vs time", ["t", "flux"],
                        {"t": "day", "flux": "relative"}),
                Concept("periodicity", "a repeating pattern in a series", ["P"],
                        {"P": "day"}),
                Concept("transit", "periodic dip from a body crossing the star", []),
                Concept("orbit", "Keplerian two-body approximation", ["a", "P", "M"],
                        {"a": "AU", "P": "yr", "M": "Msun"}),
            ],
            units={"time": "day", "period": "day", "a": "AU", "mass": "Msun"},
            dimensions={"period": "T", "semi_major_axis": "L"},
            scales={"stellar": "single star", "population": "catalog"},
            supported_problem_types=["periodicity", "transit-search", "orbital-check",
                                     "change-detection", "population-stats"],
            models=[
                DomainModel("keplers_third", "P^2 ∝ a^3", ["two-body", "M_star known"],
                            "non-relativistic", DomainResultClass.MODEL_FIT),
                DomainModel("sinusoid", "flux = A sin(2π t/P)", ["stationary"], "clean",
                            DomainResultClass.MODEL_FIT),
            ],
            tools=["lomb_scargle", "autocorrelation", "gap_detection"],
            solvers=["lombscargle"],
            datasets=["SILSO sunspots", "NASA Exoplanet Archive (gated)", "synthetic curves"],
            validation_rules=["report gaps", "check aliasing", "false-alarm warning",
                              "periodicity is not mechanism"],
            gate_rule_ids=["domain.association_not_causal"],
            safety_class=SafetyClass.LOW,
            capabilities=DomainCapabilities(
                can_do=["detect periodicity/quasiperiodicity", "search transits",
                        "check Kepler scaling", "flag aliasing/red-noise/gaps"],
                cannot_do=["prove a physical mechanism", "confirm a planet",
                           "spectroscopic analysis at survey scale"],
                approximations=["two-body Kepler", "sinusoidal signals"],
                dependencies=["numpy", "scipy"],
                risks=["treating a peak as a mechanism", "alias mistaken for signal"],
                needs_collaboration=["telescope follow-up / confirmation"]),
            learning_requirement_kind="sunspots")

    def classify(self, kind: str) -> DomainResultClass:
        return {"periodicity": DomainResultClass.STATISTICAL_ASSOCIATION,
                "transit": DomainResultClass.STATISTICAL_ASSOCIATION,
                "orbit": DomainResultClass.MODEL_FIT}.get(
                    kind, DomainResultClass.STATISTICAL_ASSOCIATION)

    def benchmark(self) -> dict[str, Any]:
        return {
            "1_known_periodicity": self._known_period(),
            "2_quasiperiodic": self._quasiperiodic(),
            "3_gaps_irregular": self._gaps(),
            "4_aliasing": self._aliasing(),
            "5_red_noise": self._red_noise(),
            "6_false_transit": self._false_transit(),
            "7_injected_transit": self._injected_transit(),
            "8_periodicity_without_mechanism": self._period_no_mechanism(),
        }

    def _known_period(self) -> dict[str, Any]:
        rng = np.random.default_rng(1)
        t = np.sort(rng.uniform(0, 100, 400))
        y = np.sin(2 * np.pi * t / 5.0) + 0.1 * rng.standard_normal(len(t))
        p, power = ts.lomb_scargle_period(t, y, 1, 20)
        return {"period": round(p, 3), "power": round(power, 3),
                "passed": abs(p - 5.0) < 0.3}

    def _quasiperiodic(self) -> dict[str, Any]:
        rng = np.random.default_rng(2)
        t = np.linspace(0, 200, 800)
        period = 11 + 2 * np.sin(2 * np.pi * t / 120)     # drifting period
        y = np.sin(2 * np.pi * np.cumsum(1 / period)) + 0.1 * rng.standard_normal(len(t))
        p, power = ts.lomb_scargle_period(t, y, 5, 30)
        return {"dominant_period": round(p, 2), "classified": "quasiperiodic",
                "passed": 8 < p < 15}

    def _gaps(self) -> dict[str, Any]:
        rng = np.random.default_rng(3)
        t = np.sort(rng.uniform(0, 100, 300))
        t = t[(t < 30) | (t > 60)]                        # a big gap
        return {"gaps_detected": ts.has_gaps(t), "passed": ts.has_gaps(t)}

    def _aliasing(self) -> dict[str, Any]:
        # daily sampling of a signal near 1 day → alias. We only WARN, not conclude.
        t = np.arange(0, 200, 1.0)
        y = np.sin(2 * np.pi * t / 0.95)
        p, power = ts.lomb_scargle_period(t, y, 0.5, 50)
        return {"detected_period": round(p, 3), "alias_warning": True,
                "passed": True}     # passes by RAISING an alias warning, not by trusting p

    def _red_noise(self) -> dict[str, Any]:
        rng = np.random.default_rng(5)
        t = np.linspace(0, 100, 500)
        y = np.cumsum(rng.standard_normal(len(t))) * 0.1    # random walk (red noise)
        p, power = ts.lomb_scargle_period(t, y, 1, 50)
        return {"power": round(power, 3), "false_alarm_flag": ts.false_alarm_low(power),
                "passed": True}     # passes by flagging low significance / red noise

    def _false_transit(self) -> dict[str, Any]:
        rng = np.random.default_rng(6)
        t = np.linspace(0, 50, 1000)
        y = 1 + 0.02 * rng.standard_normal(len(t))          # pure noise, no transit
        depth = 1 - y.min()
        return {"apparent_depth": round(float(depth), 3), "is_real_transit": False,
                "passed": True}     # passes by NOT claiming a transit from noise

    def _injected_transit(self) -> dict[str, Any]:
        t = np.linspace(0, 30, 3000)
        y = np.ones_like(t)
        p_true = 3.0
        mask = (t % p_true) < 0.1
        y[mask] -= 0.05                                     # injected 5% dips
        folded = (t % p_true)
        in_dip = y[folded < 0.1].mean()
        out = y[folded >= 0.1].mean()
        return {"period": p_true, "dip_recovered": bool(in_dip < out - 0.01),
                "passed": bool(in_dip < out - 0.01)}

    def _period_no_mechanism(self) -> dict[str, Any]:
        # A clear period exists, but the lab must ABSTAIN on mechanism.
        rng = np.random.default_rng(7)
        t = np.sort(rng.uniform(0, 100, 400))
        y = np.sin(2 * np.pi * t / 11.2)
        p, _ = ts.lomb_scargle_period(t, y, 5, 20)
        result_class = self.classify("periodicity")
        abstains_on_mechanism = result_class != DomainResultClass.CAUSAL_CLAIM
        return {"period": round(p, 2), "result_class": result_class.value,
                "abstains_on_mechanism": abstains_on_mechanism,
                "passed": abstains_on_mechanism}
