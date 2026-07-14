"""Dimensional analysis — the verifiable backbone of the First Principles Engine.

Dimensions are vectors over the 7 SI base dimensions (M, L, T, I, Θ, N, J). We can
multiply/divide/power dimensions, check equation consistency, and compute the
Buckingham-Pi dimensionless groups via the null space of the dimension matrix. This
is real, checkable math — not LLM output.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

BASE = ("M", "L", "T", "I", "Theta", "N", "J")  # mass, length, time, current, temp, amount, lum


@dataclass(frozen=True)
class Dimension:
    exps: tuple[Fraction, ...]  # length 7, aligned with BASE

    @classmethod
    def from_map(cls, **kw: float | Fraction) -> Dimension:
        return cls(tuple(Fraction(kw.get(b, 0)).limit_denominator(1000) for b in BASE))

    def __mul__(self, other: Dimension) -> Dimension:
        return Dimension(tuple(a + b for a, b in zip(self.exps, other.exps, strict=True)))

    def __truediv__(self, other: Dimension) -> Dimension:
        return Dimension(tuple(a - b for a, b in zip(self.exps, other.exps, strict=True)))

    def __pow__(self, p: float | Fraction) -> Dimension:
        pf = Fraction(p).limit_denominator(1000)
        return Dimension(tuple(a * pf for a in self.exps))

    @property
    def is_dimensionless(self) -> bool:
        return all(e == 0 for e in self.exps)

    def to_dict(self) -> dict[str, str]:
        return {b: str(e) for b, e in zip(BASE, self.exps, strict=True) if e != 0}

    def __str__(self) -> str:
        parts = [f"{b}^{e}" if e != 1 else b
                 for b, e in zip(BASE, self.exps, strict=True) if e != 0]
        return "·".join(parts) if parts else "dimensionless"


DIMENSIONLESS = Dimension.from_map()
MASS = Dimension.from_map(M=1)
LENGTH = Dimension.from_map(L=1)
TIME = Dimension.from_map(T=1)
CURRENT = Dimension.from_map(I=1)
TEMPERATURE = Dimension.from_map(Theta=1)
AMOUNT = Dimension.from_map(N=1)

VELOCITY = LENGTH / TIME
ACCELERATION = VELOCITY / TIME
FORCE = MASS * ACCELERATION                     # M L T^-2
ENERGY = FORCE * LENGTH                          # M L^2 T^-2
POWER = ENERGY / TIME
CHARGE = CURRENT * TIME
VOLTAGE = POWER / CURRENT                         # M L^2 T^-3 I^-1
RESISTANCE = VOLTAGE / CURRENT
CAPACITANCE = CHARGE / VOLTAGE
INVERSE_CAPACITANCE = VOLTAGE / CHARGE            # electrical "restoring" term (1/C)
INDUCTANCE = VOLTAGE * TIME / CURRENT
SPRING_CONSTANT = FORCE / LENGTH                  # M T^-2 (mechanical "restoring")
MECHANICAL_DAMPING = FORCE / VELOCITY             # M T^-1 (mechanical "dissipation")
FREQUENCY = DIMENSIONLESS / TIME
DIFFUSIVITY = LENGTH ** 2 / TIME

NAMED: dict[str, Dimension] = {
    "dimensionless": DIMENSIONLESS, "mass": MASS, "length": LENGTH, "time": TIME,
    "current": CURRENT, "temperature": TEMPERATURE, "amount": AMOUNT,
    "velocity": VELOCITY, "acceleration": ACCELERATION, "force": FORCE,
    "energy": ENERGY, "power": POWER, "charge": CHARGE, "voltage": VOLTAGE,
    "resistance": RESISTANCE, "capacitance": CAPACITANCE, "inductance": INDUCTANCE,
    "inverse_capacitance": INVERSE_CAPACITANCE,
    "spring_constant": SPRING_CONSTANT, "mechanical_damping": MECHANICAL_DAMPING,
    "frequency": FREQUENCY, "diffusivity": DIFFUSIVITY,
}


def named(name: str) -> Dimension:
    if name not in NAMED:
        raise KeyError(f"unknown dimension '{name}'; known: {sorted(NAMED)}")
    return NAMED[name]


def equation_consistent(lhs: Dimension, rhs: Dimension) -> bool:
    """An equation A = B is dimensionally valid iff A and B have equal dimensions."""
    return lhs.exps == rhs.exps


def sum_consistent(terms: list[Dimension]) -> bool:
    """A + B + ... requires all terms share the same dimension."""
    return all(t.exps == terms[0].exps for t in terms) if terms else True


def buckingham_pi(variables: dict[str, Dimension]) -> list[dict[str, Fraction]]:
    """Return a basis of dimensionless power-products (Pi groups) of the variables.

    Number of independent groups = n_vars - rank(dimension matrix). Uses SymPy's
    exact rational null space of the dimension matrix.
    """
    import sympy as sp

    names = list(variables)
    if not names:
        return []
    # Dimension matrix: rows = base dims, cols = variables.
    mat = sp.Matrix([[variables[n].exps[i] for n in names] for i in range(len(BASE))])
    groups: list[dict[str, Fraction]] = []
    for vec in mat.nullspace():
        # Scale to smallest integers for readability.
        denoms = [sp.nsimplify(c).q for c in vec]
        lcm = sp.ilcm(*denoms) if denoms else 1
        scaled = [sp.nsimplify(c) * lcm for c in vec]
        groups.append({names[i]: Fraction(int(scaled[i].p), int(scaled[i].q))
                       for i in range(len(names)) if scaled[i] != 0})
    return groups


def n_pi_groups(variables: dict[str, Dimension]) -> int:
    import sympy as sp

    names = list(variables)
    if not names:
        return 0
    mat = sp.Matrix([[variables[n].exps[i] for n in names] for i in range(len(BASE))])
    return len(names) - mat.rank()
