"""Property-based tests for the Discovery Engine."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from acero.discovery.confidence import ConfidenceLevel, assess_result_quality, ordinal_update
from acero.discovery.information_gain import bayesian_eig, entropy
from acero.discovery.research_utility import compute_utility

_probs = st.lists(st.floats(min_value=0.01, max_value=10.0), min_size=2, max_size=6)


@given(_probs)
def test_entropy_non_negative(vals):
    d = {f"h{i}": v for i, v in enumerate(vals)}
    assert entropy(d) >= 0.0


@given(_probs)
def test_bayesian_eig_non_negative_and_bounded(vals):
    ids = [f"h{i}" for i in range(len(vals))]
    prior = {i: 1.0 for i in ids}
    # random-ish but valid likelihoods over two outcomes
    likel = {i: {"x": abs(v) + 0.01, "y": 1.0} for i, v in zip(ids, vals, strict=True)}
    res = bayesian_eig(prior, likel)
    assert 0.0 <= res.eig <= res.prior_entropy + 1e-6


@given(
    st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1),
    st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1),
)
def test_utility_bounded(ig, sv, cc, risk):
    b = compute_utility({"information_gain": ig, "scientific_value": sv,
                         "compute_cost": cc, "risk": risk})
    assert b.utility >= 0.0
    assert 0.0 <= b.weighted_benefit <= 1.0


@given(
    st.sampled_from(list(ConfidenceLevel)),
    st.sampled_from(["supported", "weakened", "refuted", "inconclusive"]),
    st.booleans(), st.booleans(),
)
def test_ordinal_update_stays_in_range(level, outcome, repro, disc):
    q = assess_result_quality({"reproduced": repro, "discriminating": disc,
                               "status": "ok" if repro else "failed"})
    up = ordinal_update("h", level, outcome, q)
    assert int(ConfidenceLevel.REFUTED) <= int(up.updated) <= int(ConfidenceLevel.STRONGLY_SUPPORTED)
