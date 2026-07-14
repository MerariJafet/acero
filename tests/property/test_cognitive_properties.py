"""Property-based tests for the Cognitive Discovery Engine."""

from __future__ import annotations

from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st

from acero.cognitive import dimensions as d
from acero.cognitive.analogies.models import AnalogyScores

_exp = st.integers(min_value=-3, max_value=3)


@given(_exp, _exp, _exp)
def test_dimension_algebra_consistent(m, length, t):
    dim = d.Dimension.from_map(M=m, L=length, T=t)
    # dim * dim^-1 is dimensionless
    assert (dim * (dim ** Fraction(-1))).is_dimensionless
    # (dim^2)^(1/2) == dim
    assert ((dim ** 2) ** Fraction(1, 2)).exps == dim.exps


@given(st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1),
       st.floats(min_value=0, max_value=1))
def test_deep_score_weights_surface_low(structural, mathematical, surface):
    # With zero deep structure, high surface similarity cannot produce a high score.
    s = AnalogyScores(structural_similarity=0.0, mathematical_similarity=0.0,
                      invariant_preservation=0.0, predictive_transferability=0.0,
                      surface_similarity=surface)
    assert s.deep_score() <= 0.05 + 1e-9  # surface weight is 0.05


@given(st.floats(min_value=0, max_value=1))
def test_failure_risk_never_boosts_score(risk):
    base = AnalogyScores(structural_similarity=0.8, mathematical_similarity=0.8,
                         failure_risk=0.0).deep_score()
    with_risk = AnalogyScores(structural_similarity=0.8, mathematical_similarity=0.8,
                              failure_risk=risk).deep_score()
    assert with_risk <= base + 1e-9
