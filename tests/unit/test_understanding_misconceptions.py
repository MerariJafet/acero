"""Sprint 9 tests: misconception detection, negation-awareness, resolution."""

from __future__ import annotations

from acero.understanding.assessment.grading import build_evidence
from acero.understanding.learner.misconceptions import detect, resolves, severity_of
from acero.understanding.models import Criticality, EvidenceType

LEARNER = "lrn_m"


def test_detects_recovering_equation_is_law():
    ms = detect("we recovered the equation from data so it is a law we discovered",
                learner_id=LEARNER)
    assert any(m.concept == "governing_structure" for m in ms)


def test_detects_correlation_causation():
    ms = detect("the correlation proves causation here", learner_id=LEARNER)
    assert any(m.concept == "causality" for m in ms)


def test_detects_periodicity_is_mechanism():
    ms = detect("the 11.2 year period proves the dynamo mechanism", learner_id=LEARNER)
    assert any(m.concept == "mechanism_vs_pattern" for m in ms)


def test_detects_codex_as_evidence():
    ms = detect("codex said it, so that counts as evidence", learner_id=LEARNER)
    assert any(m.concept == "epistemics" for m in ms)


def test_negation_is_not_a_false_positive():
    """A correct denial of the conflation must NOT be flagged."""
    ms = detect("an analogy is structural; it does not mean the systems are identical",
                learner_id=LEARNER)
    assert not any(m.concept == "analogy" for m in ms)


def test_correct_statement_not_flagged():
    ms = detect("a good fit does not prove the true mechanism", learner_id=LEARNER)
    assert ms == []


def test_severity_lookup():
    assert severity_of("correlation_causation") == Criticality.HIGH
    assert severity_of("nonexistent") == Criticality.MEDIUM


def test_misconception_not_resolved_by_explanation_alone():
    """Resolution needs NEW passing evidence, not merely reading an explanation."""
    m = detect("recovering the equation is discovering a law", learner_id=LEARNER)[0]
    # a failing (low-score) attempt does not resolve
    weak, _ = build_evidence(LEARNER, m.concept, EvidenceType.EXPLAIN_OWN_WORDS,
                             "task", "unrelated text", ["imposed", "library", "fit"])
    assert not resolves(m, weak)


def test_misconception_resolved_by_new_correct_evidence():
    m = detect("recovering the equation is discovering a law", learner_id=LEARNER)[0]
    good, _ = build_evidence(
        LEARNER, m.concept, EvidenceType.DETECT_ERROR, "task",
        "recovering a term from an imposed library is a fit, not a discovered law",
        ["imposed", "library", "fit", "not", "law"])
    assert good.score >= 0.7
    assert resolves(m, good)


def test_reopens_if_error_recurs():
    """Evidence that re-triggers the same conflation does NOT resolve it."""
    m = detect("recovering the equation is discovering a law", learner_id=LEARNER)[0]
    ev, _ = build_evidence(
        LEARNER, m.concept, EvidenceType.EXPLAIN_OWN_WORDS, "task",
        "recovering the equation from data is discovering a law of nature",
        ["imposed", "library"])
    assert not resolves(m, ev)
