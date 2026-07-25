"""CCC-9: multidimensional uncertainty budget (offline)."""

from __future__ import annotations

from acero.science.uncertainty_budget import UncertaintyBudget


def test_combined_grows_with_each_source():
    a = UncertaintyBudget(measurement=0.2)
    b = UncertaintyBudget(measurement=0.2, causal=0.5)
    assert b.combined() > a.combined()
    assert 0.0 <= a.combined() <= 1.0


def test_zero_budget_has_zero_combined():
    assert UncertaintyBudget().combined() == 0.0


def test_dominant_source_identified():
    ub = UncertaintyBudget(measurement=0.1, causal=0.8, sampling=0.3)
    name, val = ub.dominant()
    assert name == "causal" and val == 0.8


def test_high_sources_and_report_breakdown():
    ub = UncertaintyBudget(selection=0.6, causal=0.7, model=0.2)
    highs = ub.high_sources(0.5)
    assert "selección" in highs and "causal" in highs and "modelo" not in highs
    rep = ub.report()
    assert "breakdown" in rep and rep["dominant_source"] == "causal"
    assert set(rep["breakdown"].keys()) >= {"medición", "causal", "novedad"}


def test_values_are_clamped():
    ub = UncertaintyBudget(model=5.0, sampling=-1.0)
    vals = ub._vals()
    assert vals["model"] == 1.0 and vals["sampling"] == 0.0
