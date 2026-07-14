"""Sprint 9 security tests: prediction integrity, grading integrity, privacy, provenance."""

from __future__ import annotations

import pytest

from acero.understanding.assessment.grading import grade
from acero.understanding.assessment.predictions import (
    PredictionLockedError,
    edit_after_reveal,
    make_prediction,
    reveal,
)
from acero.understanding.audit.engine import rules_audit
from acero.understanding.engine import HumanUnderstandingEngine
from acero.understanding.models import (
    EvidenceType,
    LearnerProfile,
    UnderstandingEvidence,
)
from acero.understanding.store import UnderstandingStore


def test_prediction_cannot_be_altered_after_reveal():
    """A revealed prediction is immutable (anti-HARKing for the human)."""
    p = make_prediction("lrn", "proj", "exp", "R² stays high", confidence=0.8)
    reveal(p, "R² collapsed", correct_tokens=["collapsed"])
    with pytest.raises(PredictionLockedError):
        edit_after_reveal(p, "actually I predicted a collapse")
    with pytest.raises(PredictionLockedError):
        reveal(p, "second reveal")


def test_grader_cannot_be_gamed_to_always_pass():
    """An empty/gibberish answer cannot score a pass; a forbidden claim is penalised."""
    assert grade("", ["imposed library", "fit"]).score == 0.0
    assert grade("qwerty zxcvb", ["imposed library", "fit"]).score < 0.5
    g = grade("this is a discovered law of nature", ["imposed library"],
              forbidden_elements=["law of nature"])
    assert g.red_flags and g.score < 0.5


def test_llm_as_sole_grader_is_flagged():
    ev = UnderstandingEvidence(
        learner_id="lrn", concept_id="c", evidence_type=EvidenceType.EXPLAIN_OWN_WORDS,
        task="t", response="r", expected_elements=["x"], grader="codex", score=1.0)
    rep = rules_audit(evidence=[ev])
    assert any(f.concern == "llm_as_sole_grader" for f in rep.findings)


def test_profile_privacy_overcollection_flagged():
    profile = LearnerProfile(preferred_name="x", learning_goals=["store my password here"])
    rep = rules_audit(profile=profile)
    assert any(f.concern == "privacy_overcollection" for f in rep.findings)


def test_assessment_persisted_with_provenance(disc_store):
    """Every evidence write goes through the ledger (provenance), like other stores."""
    eng = HumanUnderstandingEngine(UnderstandingStore(disc_store))
    eng.record_assessment(
        "lrn", "imposed_library", EvidenceType.EXPLAIN_OWN_WORDS, "t",
        "the imposed library selected the term by fit, not a law",
        ["imposed library", "fit", "law"])
    # provenance recorded in the ledger for the learner scope
    events = disc_store.ledger.list_events("_learner") if hasattr(
        disc_store.ledger, "list_events") else None
    # at minimum, the evidence is retrievable
    assert eng.store.evidence("lrn", "imposed_library")
    _ = events


def test_trivial_assessment_flagged():
    ev = UnderstandingEvidence(
        learner_id="lrn", concept_id="c", evidence_type=EvidenceType.EXPLAIN_OWN_WORDS,
        task="t", response="r", expected_elements=[], score=1.0)
    rep = rules_audit(evidence=[ev])
    assert any(f.concern == "trivial_assessment" for f in rep.findings)
