"""Sensitivity fix: cross-check keys on NUMBERS reproducing, not identical verdict labels
(that was degrading real positives). Opposite verdicts with same numbers stay a
contradiction."""
from __future__ import annotations

from acero.portal.experiment_factory import _compare_results, build_codegen_prompt


def test_same_numbers_verdict_variance_is_agreement():
    a = {"verdict": "supports", "metrics": {"beta": 0.30, "p": 0.01}}
    b = {"verdict": "inconclusive", "metrics": {"beta": 0.31, "p": 0.011}}
    agreed, note = _compare_results(a, b)
    assert agreed is True                      # numbers reproduce -> not degraded
    assert "varianza de codegen" in note


def test_opposite_verdicts_same_numbers_is_contradiction():
    a = {"verdict": "supports", "metrics": {"x": 1.0}}
    b = {"verdict": "refutes", "metrics": {"x": 1.0}}
    agreed, note = _compare_results(a, b)
    assert agreed is False and "contradicción" in note


def test_divergent_numbers_still_fail():
    a = {"verdict": "supports", "metrics": {"x": 1.0}}
    assert _compare_results(a, {"verdict": "supports", "metrics": {"x": 3.0}})[0] is False


def test_codegen_prompt_has_proportional_complexity_rule():
    p = build_codegen_prompt({"title": "t", "what": "", "how": "", "controls": "",
                              "discriminator": ""}, {"title": "h"}, [], {})
    assert "COMPLEJIDAD PROPORCIONAL" in p
