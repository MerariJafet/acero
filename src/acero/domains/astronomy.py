"""Astronomy domain plugin — orbital mechanics (computational only)."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .base import BenchmarkCase, BenchmarkResult, DomainPlugin, ValidationResult


class AstronomyPlugin(DomainPlugin):
    name = "astronomy"
    domain = "astronomy"
    units = {
        "distance": "AU", "time": "yr", "mass": "M_sun",
        "angle": "deg", "velocity": "km/s",
    }
    allowed_tools = ["kepler_period", "circular_orbital_velocity", "magnitude_distance"]
    risks = [
        "Modelos de dos cuerpos / kepleriano idealizado.",
        "Se ignoran perturbaciones y relatividad salvo indicación.",
        "Datos sintéticos o públicos; sin observación física.",
    ]

    def _simulators(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "kepler_period": self._kepler_period,
            "circular_orbital_velocity": self._orbital_velocity,
            "magnitude_distance": self._magnitude_distance,
        }

    def _kepler_period(self, p: dict[str, Any]) -> dict[str, Any]:
        # P[yr] = sqrt(a[AU]^3 / M[M_sun]); Kepler's third law in solar units.
        a = float(p["a_au"])
        m = float(p.get("total_mass_msun", 1.0))
        period = math.sqrt(a ** 3 / m)
        return {"period_yr": period}

    def _orbital_velocity(self, p: dict[str, Any]) -> dict[str, Any]:
        # v = sqrt(G M / r); use SI. G in m^3 kg^-1 s^-2, masses in kg, r in m.
        G = 6.67430e-11
        m_kg = float(p["mass_kg"])
        r_m = float(p["radius_m"])
        v = math.sqrt(G * m_kg / r_m)
        return {"velocity_m_s": v, "velocity_km_s": v / 1000.0}

    def _magnitude_distance(self, p: dict[str, Any]) -> dict[str, Any]:
        # distance modulus: m - M = 5 log10(d_pc) - 5
        m = float(p["apparent_mag"])
        M = float(p["absolute_mag"])
        d_pc = 10 ** ((m - M + 5) / 5)
        return {"distance_pc": d_pc}

    def validate(self, kind: str, data: dict[str, Any]) -> ValidationResult:
        for key in ("a_au", "total_mass_msun", "mass_kg", "radius_m"):
            if key in data and float(data[key]) <= 0:
                return ValidationResult.invalid(key, f"{key} must be positive")
        return ValidationResult.valid()

    def project_template(self) -> str:
        return (
            "# Proyecto de Astronomía (computacional)\n\n"
            "- Pregunta:\n- Objeto/sistema y unidades (AU, yr, M_sun):\n"
            "- Hipótesis competidoras:\n- Simulador(es): kepler_period | "
            "circular_orbital_velocity | magnitude_distance\n"
            "- Fuente de datos (pública/sintética) + licencia:\n- Límite del modelo:\n"
        )

    def benchmark(self) -> BenchmarkResult:
        cases: list[BenchmarkCase] = []
        # Earth: a=1 AU, M=1 M_sun -> P = 1 yr
        p_earth = self._kepler_period({"a_au": 1.0, "total_mass_msun": 1.0})["period_yr"]
        cases.append(BenchmarkCase("earth_period_yr", 1.0, p_earth, 1e-9))
        # a=4 AU, M=1 -> P = sqrt(64) = 8 yr
        p4 = self._kepler_period({"a_au": 4.0})["period_yr"]
        cases.append(BenchmarkCase("a4_period_yr", 8.0, p4, 1e-9))
        # distance modulus: m=M -> d = 10 pc
        d = self._magnitude_distance({"apparent_mag": 5.0, "absolute_mag": 5.0})["distance_pc"]
        cases.append(BenchmarkCase("distance_10pc", 10.0, d, 1e-6))
        return BenchmarkResult(domain=self.domain, cases=cases)
