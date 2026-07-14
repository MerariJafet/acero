"""Property-based tests for World Model beliefs."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from acero.world_model.belief import BeliefPolicy, BeliefState


@given(
    ev=st.floats(min_value=0, max_value=50),
    ctr=st.floats(min_value=0, max_value=50),
    reps=st.integers(min_value=0, max_value=20),
    negs=st.integers(min_value=0, max_value=10),
    contras=st.integers(min_value=0, max_value=10),
)
def test_confidence_always_in_bounds(ev, ctr, reps, negs, contras):
    b = BeliefState(evidence_strength=ev, counter_strength=ctr, replication_count=reps,
                    negative_results=negs, contradictions=contras, distinct_sources=2)
    c = b.derive_confidence(BeliefPolicy())
    assert 0.0 <= c <= BeliefPolicy().max_confidence


@given(ev=st.floats(min_value=0.1, max_value=20), extra=st.floats(min_value=0.1, max_value=20))
def test_more_evidence_monotonic_non_decreasing(ev, extra):
    policy = BeliefPolicy()
    low = BeliefState(evidence_strength=ev, distinct_sources=2).derive_confidence(policy)
    high = BeliefState(evidence_strength=ev + extra, distinct_sources=2).derive_confidence(policy)
    assert high >= low - 1e-9


@given(contras=st.integers(min_value=1, max_value=10))
def test_contradictions_never_increase_confidence(contras):
    policy = BeliefPolicy()
    base = BeliefState(evidence_strength=5.0, distinct_sources=3).derive_confidence(policy)
    with_contra = BeliefState(evidence_strength=5.0, distinct_sources=3,
                              contradictions=contras).derive_confidence(policy)
    assert with_contra <= base
