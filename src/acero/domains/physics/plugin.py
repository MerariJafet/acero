"""Physics domain plugin — classical mechanics & thermal (computational only)."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from ..base import BenchmarkCase, BenchmarkResult, DomainPlugin, ValidationResult

G_EARTH = 9.80665  # m/s^2


class PhysicsPlugin(DomainPlugin):
    name = "physics"
    domain = "physics"
    units = {
        "length": "m", "mass": "kg", "time": "s", "temperature": "K",
        "velocity": "m/s", "acceleration": "m/s^2", "force": "N", "energy": "J",
    }
    allowed_tools = ["projectile_range", "newton_cooling", "damped_oscillator_period"]
    risks = [
        "Modelos idealizados (sin fricción del aire salvo indicado).",
        "Régimen de validez limitado (p. ej. pequeñas oscilaciones).",
        "Simulación ≠ medición física.",
    ]

    def _simulators(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "projectile_range": self._projectile_range,
            "newton_cooling": self._newton_cooling,
            "damped_oscillator_period": self._damped_period,
        }

    def _projectile_range(self, p: dict[str, Any]) -> dict[str, Any]:
        v0 = float(p["v0"])
        angle_deg = float(p["angle_deg"])
        g = float(p.get("g", G_EARTH))
        theta = math.radians(angle_deg)
        rng = (v0 ** 2) * math.sin(2 * theta) / g
        t_flight = 2 * v0 * math.sin(theta) / g
        return {"range_m": rng, "time_of_flight_s": t_flight}

    def _newton_cooling(self, p: dict[str, Any]) -> dict[str, Any]:
        T_env = float(p["T_env"])
        T0 = float(p["T0"])
        k = float(p["k"])
        t = float(p["t"])
        temp = T_env + (T0 - T_env) * math.exp(-k * t)
        half_life = math.log(2) / k if k > 0 else float("inf")
        return {"temperature": temp, "half_life": half_life}

    def _damped_period(self, p: dict[str, Any]) -> dict[str, Any]:
        m = float(p["m"])
        k = float(p["k"])
        c = float(p.get("c", 0.0))
        w0 = math.sqrt(k / m)
        zeta = c / (2 * math.sqrt(k * m)) if k * m > 0 else 0.0
        if zeta >= 1.0:
            return {"underdamped": False, "zeta": zeta, "period_s": None}
        wd = w0 * math.sqrt(1 - zeta ** 2)
        return {"underdamped": True, "zeta": zeta, "period_s": 2 * math.pi / wd}

    def validate(self, kind: str, data: dict[str, Any]) -> ValidationResult:
        if "mass" in data and float(data["mass"]) <= 0:
            return ValidationResult.invalid("mass", "mass must be positive")
        if "m" in data and float(data["m"]) <= 0:
            return ValidationResult.invalid("m", "mass must be positive")
        if kind == "projectile":
            a = float(data.get("angle_deg", 45))
            if not 0 <= a <= 90:
                return ValidationResult.invalid("angle_deg", "angle must be in [0, 90]")
        return ValidationResult.valid()

    def project_template(self) -> str:
        return (
            "# Proyecto de Física (computacional)\n\n"
            "- Pregunta:\n- Sistema y variables (con unidades SI):\n"
            "- Hipótesis competidoras:\n- Simulador(es): projectile_range | "
            "newton_cooling | damped_oscillator_period\n- Validación fuera de rango:\n"
            "- Límite de validez del modelo:\n"
        )

    def benchmark(self) -> BenchmarkResult:
        cases: list[BenchmarkCase] = []
        # 45° maximises range: v0=10, g=9.80665 -> 10^2/g
        r = self._projectile_range({"v0": 10, "angle_deg": 45})["range_m"]
        cases.append(BenchmarkCase("projectile_45deg", 100 / G_EARTH, r, 1e-6))
        # cooling half-life for k=ln2 -> 1.0
        hl = self._newton_cooling({"T_env": 20, "T0": 80, "k": math.log(2), "t": 0})["half_life"]
        cases.append(BenchmarkCase("cooling_half_life", 1.0, hl, 1e-9))
        # undamped period m=1,k=(2pi)^2 -> period 1.0
        per = self._damped_period({"m": 1.0, "k": (2 * math.pi) ** 2, "c": 0.0})["period_s"]
        cases.append(BenchmarkCase("undamped_period", 1.0, per, 1e-9))
        return BenchmarkResult(domain=self.domain, cases=cases)
