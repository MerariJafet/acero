"""Dimensional analysis and Buckingham Pi tests."""

from __future__ import annotations

from fractions import Fraction

from acero.cognitive import dimensions as d


def test_equation_consistency():
    assert d.equation_consistent(d.FORCE, d.MASS * d.ACCELERATION)
    assert d.equation_consistent(d.ENERGY, d.MASS * d.VELOCITY ** 2)
    assert not d.equation_consistent(d.FORCE, d.MASS * d.VELOCITY)  # F != m v


def test_dimensionless_detection():
    assert (d.FORCE / d.FORCE).is_dimensionless
    assert not d.ENERGY.is_dimensionless


def test_sum_consistency():
    assert d.sum_consistent([d.ENERGY, d.ENERGY])
    assert not d.sum_consistent([d.ENERGY, d.FORCE])


def test_pendulum_buckingham_pi():
    variables = {"period": d.TIME, "length": d.LENGTH, "gravity": d.ACCELERATION, "mass": d.MASS}
    assert d.n_pi_groups(variables) == 1
    groups = d.buckingham_pi(variables)
    assert len(groups) == 1
    g = groups[0]
    # T^2 * g / L is the dimensionless group; mass must NOT appear.
    assert "mass" not in g
    # normalise: period exponent should be ±2 relative to length ∓1, gravity ±1
    assert abs(g["period"]) == 2 and abs(g["length"]) == 1 and abs(g["gravity"]) == 1


def test_damping_ratio_dimensionless_mechanical_and_electrical():
    # Mechanical: c / sqrt(m*k) dimensionless
    m, c, k = d.MASS, d.MECHANICAL_DAMPING, d.SPRING_CONSTANT
    assert (c / ((m * k) ** Fraction(1, 2))).is_dimensionless
    # Electrical: R / sqrt(L * (1/C)) dimensionless
    L, R, invC = d.INDUCTANCE, d.RESISTANCE, d.INVERSE_CAPACITANCE
    assert (R / ((L * invC) ** Fraction(1, 2))).is_dimensionless


def test_fourier_number_dimensionless():
    assert (d.DIFFUSIVITY * d.TIME / (d.LENGTH ** 2)).is_dimensionless


def test_kinetic_energy_pi():
    # E, m, v -> one dimensionless group E/(m v^2)
    variables = {"energy": d.ENERGY, "mass": d.MASS, "velocity": d.VELOCITY}
    assert d.n_pi_groups(variables) == 1
