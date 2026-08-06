"""Formal (symbolic) verification with sympy — proved | refuted | unknown."""
from __future__ import annotations

from acero.science.formal_verify import verify


def test_true_identity_is_proved():
    r = verify("identity", lhs="sin(x)**2 + cos(x)**2", rhs="1")
    assert r["result"] == "proved"


def test_false_identity_is_refuted_with_counterexample():
    r = verify("identity", lhs="(x+1)**2", rhs="x**2 + 1")
    assert r["result"] == "refuted" and "counterexample" in r


def test_always_true_inequality_is_proved():
    r = verify("inequality", expr="x**2 + 1 > 0", var="x")
    assert r["result"] == "proved"


def test_inequality_false_somewhere_is_refuted():
    r = verify("inequality", expr="x > 0", var="x")     # false for x <= 0
    assert r["result"] == "refuted"


def test_inequality_true_on_a_bounded_domain():
    r = verify("inequality", expr="x > 0", var="x", domain=(1, 10))
    assert r["result"] == "proved"


def test_limit_proved():
    r = verify("limit", expr="sin(x)/x", var="x", to="0", expected="1")
    assert r["result"] == "proved"


def test_limit_refuted():
    r = verify("limit", expr="sin(x)/x", var="x", to="0", expected="0")
    assert r["result"] == "refuted"


def test_boolean_tautology_and_contradiction():
    assert verify("boolean", expr="Or(a, Not(a))")["result"] == "proved"
    assert verify("boolean", expr="And(a, Not(a))")["result"] == "refuted"


def test_malformed_claim_is_unknown_not_crash():
    r = verify("identity", lhs="))(", rhs="1")
    assert r["result"] == "unknown"
    assert verify("nonsense_kind")["result"] == "unknown"
