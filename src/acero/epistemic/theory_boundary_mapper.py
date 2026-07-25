"""F3 — Theory boundary mapper: where was a claim validated vs where is it applied.

A domain limit is not a refutation (reviewer's discipline), but applying a claim OUTSIDE
its validated boundary is an extrapolation vulnerability. This maps the validated domain
and flags application ranges that fall outside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BoundaryCondition:
    variable: str
    validated_min: float
    validated_max: float

    def contains(self, value: float) -> bool:
        return self.validated_min <= value <= self.validated_max


@dataclass
class BoundaryMap:
    claim_id: str
    conditions: list[BoundaryCondition] = field(default_factory=list)

    def add(self, variable: str, vmin: float, vmax: float) -> None:
        self.conditions.append(BoundaryCondition(variable, vmin, vmax))

    def extrapolations(self, application: dict[str, float]) -> list[str]:
        """Variables whose application value falls OUTSIDE the validated range."""
        out: list[str] = []
        by_var = {c.variable: c for c in self.conditions}
        for var, val in application.items():
            c = by_var.get(var)
            if c is not None and not c.contains(val):
                out.append(f"{var}={val} fuera del rango validado "
                           f"[{c.validated_min}, {c.validated_max}]")
            elif c is None:
                out.append(f"{var}: sin rango validado declarado (extrapolación implícita)")
        return out

    def is_within_domain(self, application: dict[str, float]) -> bool:
        return not self.extrapolations(application)
