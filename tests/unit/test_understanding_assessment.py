"""Sprint 9 tests: explanations, grading, predictions, transfer, exercises."""

from __future__ import annotations

import pytest

from acero.understanding.assessment.exercises import (
    SolutionWithheldError,
    reveal_solution,
    sindy_exercises,
)
from acero.understanding.assessment.grading import grade
from acero.understanding.assessment.predictions import (
    PredictionLockedError,
    edit_after_reveal,
    honest_uncertainty,
    is_overconfident,
    make_prediction,
    reveal,
)
from acero.understanding.assessment.transfer import assess_transfer, get_task
from acero.understanding.explanation.levels import build_levels, explain_mode
from acero.understanding.models import ExplainMode, ExplanationLevel

LEARNER = "lrn_a"


# --- explanations ---------------------------------------------------------

def test_build_levels_produces_five_distinct_levels():
    arts = build_levels(
        "damped", phenomenon="damped oscillation", variables=["x", "v"],
        mechanism="restoring force minus friction", assumptions=["linear damping"],
        equations=["dv/dt = -4x - 0.5v"], code_references=["engine.py"],
        evidence_references=["bench.py"], limitations=["polynomial library imposed"])
    assert {a.level for a in arts} == set(ExplanationLevel)


def test_explanation_requires_limitations():
    with pytest.raises(ValueError):
        build_levels("x", phenomenon="p", variables=["x"], mechanism="m",
                     assumptions=[], equations=[], code_references=[],
                     evidence_references=[], limitations=[])


def test_abstention_must_have_concrete_reason():
    with pytest.raises(ValueError):
        explain_mode(ExplainMode.EXPLAIN_ABSTENTION, reasons={})
    ok = explain_mode(ExplainMode.EXPLAIN_ABSTENTION,
                      reasons={"EXPLAIN_ABSTENTION": ["parameter not identifiable"]})
    assert "not identifiable" in ok


# --- grading --------------------------------------------------------------

def test_grade_partial_credit():
    g = grade("mentions the imposed library only",
              ["imposed library", "fit not law", "system identification"])
    assert 0.0 < g.score < 1.0
    assert "imposed library" in g.matched


def test_grade_penalises_forbidden_claim():
    g = grade("this recovered equation is a law of nature",
              ["imposed library"], forbidden_elements=["law of nature"])
    assert g.red_flags == ["law of nature"]
    assert g.score < 0.5


def test_grade_empty_rubric_flagged():
    g = grade("anything", [])
    assert g.score == 0.0
    assert g.red_flags


# --- predictions ----------------------------------------------------------

def test_prediction_locked_after_reveal():
    p = make_prediction(LEARNER, "proj", "exp", "R² stays near 1", confidence=0.8)
    reveal(p, "R² dropped to 0.29", correct_tokens=["0.29", "dropped"])
    assert p.locked
    with pytest.raises(PredictionLockedError):
        reveal(p, "changed my mind")
    with pytest.raises(PredictionLockedError):
        edit_after_reveal(p, "new text")


def test_overconfidence_and_honest_uncertainty():
    over = make_prediction(LEARNER, "p", "e", "it stays flat", confidence=0.9)
    reveal(over, "big change", correct_tokens=["big", "change"])
    assert is_overconfident(over)

    honest = make_prediction(LEARNER, "p", "e", "it stays flat", confidence=0.3)
    reveal(honest, "big change", correct_tokens=["big", "change"])
    assert honest_uncertainty(honest)
    assert not is_overconfident(honest)


# --- transfer -------------------------------------------------------------

def test_transfer_pass_and_fail():
    ev, _ = assess_transfer(
        LEARNER, "identifiability",
        "No, K is not identifiable — the data never approaches capacity so it does not "
        "constrain K.")
    assert ev.score >= 0.7

    bad, grade_r = assess_transfer(LEARNER, "identifiability",
                                   "K is uniquely determined by the fit.")
    assert bad.score < 0.5
    assert grade_r.red_flags


def test_transfer_task_lookup():
    t = get_task("diffusion")
    assert t.source_domain == "thermal"
    with pytest.raises(KeyError):
        get_task("nope")


# --- exercises ------------------------------------------------------------

def test_solution_withheld_before_attempt():
    ex = sindy_exercises("proj")[0]
    with pytest.raises(SolutionWithheldError):
        reveal_solution(ex, attempted=False)
    assert reveal_solution(ex, attempted=True) == ex.solution
