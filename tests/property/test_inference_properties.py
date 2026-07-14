"""Property-based tests for the inference engine."""
from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from acero.inference.audit.gate import GateInput, GateStatus, evaluate
from acero.inference.discovery.sparse_identification import stlsq


@given(k=st.floats(min_value=0.1, max_value=3.0), seed=st.integers(0, 1000))
@settings(max_examples=15, deadline=None)
def test_stlsq_recovers_linear_slope(k, seed):
    rng = np.random.default_rng(seed)
    x = rng.uniform(1, 5, size=200)
    theta = np.column_stack([np.ones_like(x), x])
    y = k * x                      # dy = k*x, no constant
    xi = stlsq(theta, y, threshold=0.05)
    assert abs(xi[1] - k) < 0.05   # slope recovered
    assert abs(xi[0]) < 0.1        # spurious constant suppressed (ridge leaves a small bias)


@given(
    dims=st.booleans(), repro=st.booleans(), leak=st.booleans(),
    codex=st.booleans(),
)
def test_any_critical_violation_blocks(dims, repro, leak, codex):
    gi = GateInput(dimensions_valid=dims, reproduced=repro, train_test_disjoint=leak,
                   codex_treated_as_evidence=codex)
    rep = evaluate(gi)
    violated = (not dims) or (not repro) or (not leak) or codex
    if violated:
        assert rep.status == GateStatus.BLOCKED
