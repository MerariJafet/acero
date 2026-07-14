"""Chemistry domain plugin — computational stoichiometry & gas laws.

STRICTLY computational: molar masses, ideal-gas relations, stoichiometry. NO
synthesis procedures, NO hazardous reactions, NO lab protocols.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from ..base import BenchmarkCase, BenchmarkResult, DomainPlugin, ValidationResult

R_GAS = 8.314462618  # J/(mol*K)

# Atomic masses (g/mol) for common elements — enough for the benchmark set.
ATOMIC_MASS = {
    "H": 1.008, "He": 4.0026, "C": 12.011, "N": 14.007, "O": 15.999,
    "Na": 22.990, "Mg": 24.305, "S": 32.06, "Cl": 35.45, "K": 39.098,
    "Ca": 40.078, "Fe": 55.845, "P": 30.974,
}

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")


class ChemistryPlugin(DomainPlugin):
    name = "chemistry"
    domain = "chemistry"
    units = {
        "amount": "mol", "mass": "g", "pressure": "Pa",
        "volume": "m^3", "temperature": "K", "molar_mass": "g/mol",
    }
    allowed_tools = ["molar_mass", "ideal_gas", "moles_from_mass"]
    risks = [
        "Solo cálculo; sin síntesis ni procedimientos de laboratorio.",
        "Prohibido diseñar reacciones peligrosas o toxinas (research_safety).",
        "Gases ideales; sin correcciones de gas real salvo indicación.",
    ]

    def _simulators(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "molar_mass": self._molar_mass,
            "ideal_gas": self._ideal_gas,
            "moles_from_mass": self._moles_from_mass,
        }

    def _parse_formula(self, formula: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        pos = 0
        for m in _TOKEN.finditer(formula):
            if m.group(0) == "":
                continue
            el, num = m.group(1), m.group(2)
            counts[el] = counts.get(el, 0) + (int(num) if num else 1)
            pos = m.end()
        if pos != len(formula.strip()):
            raise ValueError(f"Unparseable formula: {formula!r}")
        return counts

    def _molar_mass(self, p: dict[str, Any]) -> dict[str, Any]:
        formula = str(p["formula"])
        counts = self._parse_formula(formula)
        unknown = [el for el in counts if el not in ATOMIC_MASS]
        if unknown:
            raise ValueError(f"Unknown element(s): {unknown}")
        mass = sum(ATOMIC_MASS[el] * n for el, n in counts.items())
        return {"molar_mass_g_mol": round(mass, 4), "composition": counts}

    def _moles_from_mass(self, p: dict[str, Any]) -> dict[str, Any]:
        mass_g = float(p["mass_g"])
        mm = self._molar_mass({"formula": p["formula"]})["molar_mass_g_mol"]
        return {"moles": mass_g / mm}

    def _ideal_gas(self, p: dict[str, Any]) -> dict[str, Any]:
        # Solve PV = nRT for the single missing variable (given as None or absent).
        present = {k: p[k] for k in ("P", "V", "n", "T") if p.get(k) is not None}
        if len(present) != 3:
            raise ValueError("ideal_gas needs exactly 3 of {P, V, n, T}")
        if "P" not in present:
            return {"P": float(present["n"]) * R_GAS * float(present["T"]) / float(present["V"])}
        if "V" not in present:
            return {"V": float(present["n"]) * R_GAS * float(present["T"]) / float(present["P"])}
        if "n" not in present:
            return {"n": float(present["P"]) * float(present["V"]) / (R_GAS * float(present["T"]))}
        return {"T": float(present["P"]) * float(present["V"]) / (float(present["n"]) * R_GAS)}

    def validate(self, kind: str, data: dict[str, Any]) -> ValidationResult:
        if kind == "formula" and "formula" in data:
            try:
                counts = self._parse_formula(str(data["formula"]))
            except ValueError as exc:
                return ValidationResult.invalid("formula", str(exc))
            unknown = [el for el in counts if el not in ATOMIC_MASS]
            if unknown:
                return ValidationResult.invalid("formula", f"unknown elements {unknown}")
        for key in ("mass_g", "P", "V", "n", "T"):
            if key in data and data[key] is not None and float(data[key]) < 0:
                return ValidationResult.invalid(key, f"{key} must be non-negative")
        return ValidationResult.valid()

    def project_template(self) -> str:
        return (
            "# Proyecto de Química Computacional\n\n"
            "- Pregunta:\n- Especies/fórmulas y unidades (mol, g, Pa, m^3, K):\n"
            "- Hipótesis competidoras:\n- Herramientas: molar_mass | ideal_gas | "
            "moles_from_mass\n- Supuestos (gas ideal, etc.):\n"
            "- NOTA: sin síntesis ni laboratorio; solo cómputo.\n"
        )

    def benchmark(self) -> BenchmarkResult:
        cases: list[BenchmarkCase] = []
        h2o = self._molar_mass({"formula": "H2O"})["molar_mass_g_mol"]
        cases.append(BenchmarkCase("molar_mass_H2O", 18.015, h2o, 0.01))
        co2 = self._molar_mass({"formula": "CO2"})["molar_mass_g_mol"]
        cases.append(BenchmarkCase("molar_mass_CO2", 44.009, co2, 0.01))
        # 1 mol ideal gas at STP-ish (T=273.15 K, P=101325 Pa) -> V ~ 0.022414 m^3
        v = self._ideal_gas({"n": 1.0, "T": 273.15, "P": 101325})["V"]
        cases.append(BenchmarkCase("molar_volume_stp", 0.022414, v, 1e-4))
        return BenchmarkResult(domain=self.domain, cases=cases)
