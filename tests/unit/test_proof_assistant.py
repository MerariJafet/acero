"""Tests for Gödel — the Z3-backed mechanized prover (beyond sympy)."""

from __future__ import annotations

import pytest

from acero.science import proof_assistant as ga

z3 = pytest.importorskip("z3")  # these need the Z3 backend installed


def test_universal_integer_inequality_is_proved():
    # ∀ integer n: n*n >= 0  — sympy-hard as a *logic* statement, trivial for Z3
    r = ga.prove("int_forall", expr="n*n >= 0", vars=["n"])
    assert r["result"] == "proved" and r["backend"] == "z3"


def test_false_universal_is_refuted_with_counterexample():
    r = ga.prove("int_forall", expr="n >= 0", vars=["n"])
    assert r["result"] == "refuted" and "counterexample" in r


def test_universal_under_hypotheses():
    # ∀ n,m: (n>=0 ∧ m>=0) → n+m >= 0   — quantified reasoning with assumptions
    r = ga.prove("int_forall", expr="n + m >= 0", vars=["n", "m"],
                 assume=["n >= 0", "m >= 0"])
    assert r["result"] == "proved"


def test_boolean_tautology_is_proved():
    r = ga.prove("bool_forall", expr="Or(a, Not(a))", vars=["a"], sort="bool")
    assert r["result"] == "proved"


def test_satisfiable_witness():
    r = ga.prove("int_exists", expr="And(n > 5, n < 8)", vars=["n"])
    assert r["result"] == "proved" and "witness" in r


def test_bad_expression_is_unknown_not_crash():
    r = ga.prove("int_forall", expr="))(", vars=["n"])
    assert r["result"] == "unknown"
    assert ga.prove("nonsense_kind", expr="n>=0", vars=["n"])["result"] == "unknown"
