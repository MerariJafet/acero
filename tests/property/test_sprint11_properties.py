"""Sprint 11 property tests: tokens and evidence dependency invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from acero.epistemic_gate.tokens import TokenError, TokenRegistry
from acero.reliability.evidence import DependencyGraph, Evidence


@given(
    n_dup=st.integers(min_value=1, max_value=8),
    n_indep=st.integers(min_value=0, max_value=6),
)
@settings(max_examples=40, deadline=None)
def test_dependent_evidence_never_inflates_independent_count(n_dup, n_indep):
    g = DependencyGraph()
    for i in range(n_dup):
        g.add(Evidence(id=f"dup{i}", dataset="SAME"))
    for j in range(n_indep):
        g.add(Evidence(id=f"ind{j}", dataset=f"D{j}"))
    g.build()
    # duplicates collapse to 1 cluster; independents each stand alone
    expected = (1 if n_dup else 0) + n_indep
    assert g.effective_independent_count() == expected
    assert g.effective_independent_count() <= n_dup + n_indep


@given(
    action=st.sampled_from(["update_belief", "link", "promote"]),
    other=st.sampled_from(["update_belief", "link", "promote"]),
)
@settings(max_examples=40, deadline=None)
def test_token_only_authorises_its_own_action(action, other):
    reg = TokenRegistry(ttl_seconds=30)
    tok = reg.issue(action=action, project_id="p")
    if other == action:
        reg.validate(tok, action=other, project_id="p")   # ok
    else:
        try:
            reg.validate(tok, action=other, project_id="p")
            raised = False
        except TokenError:
            raised = True
        assert raised


@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=20, deadline=None)
def test_token_single_use(n_replays):
    reg = TokenRegistry(ttl_seconds=30)
    tok = reg.issue(action="a", project_id="p")
    reg.validate(tok, action="a", project_id="p")
    reg.spend(tok)
    for _ in range(n_replays):
        try:
            reg.validate(tok, action="a", project_id="p")
            raised = False
        except TokenError:
            raised = True
        assert raised
