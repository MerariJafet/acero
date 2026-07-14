"""Sprint 9 tests: learner knowledge-state machine, confidence, decay, persistence."""

from __future__ import annotations

from acero.understanding.assessment.grading import build_evidence
from acero.understanding.learner.confidence import assess as assess_calibration
from acero.understanding.learner.history import (
    LearningEvent,
    LearningHistory,
    is_decayed,
    next_review,
)
from acero.understanding.learner.knowledge_state import (
    MASTERY_MIN_DISTINCT_EVIDENCE,
    apply_evidence,
    overconfidence_gap,
)
from acero.understanding.models import (
    Criticality,
    EvidenceType,
    KnowledgeState,
    KnowledgeStatus,
)
from acero.understanding.store import UnderstandingStore

LEARNER = "lrn_test"


def _ev(concept, etype, response, expected, *, confidence=0.5):
    ev, _ = build_evidence(LEARNER, concept, etype, "task", response, expected,
                           confidence=confidence)
    return ev


def test_passing_evidence_advances_one_rung():
    st = KnowledgeState(concept_id="c", learner_id=LEARNER)
    ev = _ev("c", EvidenceType.EXPLAIN_OWN_WORDS, "the imposed library matters",
             ["imposed library"])
    out = apply_evidence(st, ev)
    assert out.advanced
    assert st.status == KnowledgeStatus.RECOGNIZED


def test_failing_evidence_never_advances_beyond_exposed():
    st = KnowledgeState(concept_id="c", learner_id=LEARNER)
    ev = _ev("c", EvidenceType.EXPLAIN_OWN_WORDS, "unrelated words", ["imposed library"])
    out = apply_evidence(st, ev)
    assert st.status == KnowledgeStatus.EXPOSED
    assert not (out.to_status == KnowledgeStatus.RECOGNIZED)


def test_single_correct_answer_does_not_grant_mastery():
    """A single passing answer can never reach MASTERED."""
    st = KnowledgeState(concept_id="c", learner_id=LEARNER)
    ev = _ev("c", EvidenceType.TRANSFER, "applies to a new domain", ["applies", "new"])
    apply_evidence(st, ev, distinct_evidence_kinds=set())
    assert st.status != KnowledgeStatus.MASTERED


def test_mastery_requires_multiple_distinct_evidence_kinds():
    st = KnowledgeState(concept_id="c", learner_id=LEARNER)
    kinds: set[EvidenceType] = set()
    ladder = [
        (EvidenceType.EXPLAIN_OWN_WORDS,
         "explains clearly why the imposed library shapes the recovered terms",
         ["imposed", "library"]),
        (EvidenceType.MODIFY_CODE,
         "modified the sensitivity script and re-ran it several times",
         ["modified", "re-ran"]),
        (EvidenceType.DETECT_ERROR,
         "detects the fit-versus-mechanism conflation error in the claim",
         ["detects", "error"]),
        (EvidenceType.TRANSFER,
         "transfers the idea to an unrelated population-growth domain",
         ["transfers", "domain"]),
        (EvidenceType.PROPOSE_FALSIFICATION,
         "proposes a concrete falsification test that would refute the model",
         ["proposes", "falsification"]),
    ]
    for etype, resp, exp in ladder:
        ev = _ev("c", etype, resp, exp)
        apply_evidence(st, ev, distinct_evidence_kinds=kinds)
        kinds.add(etype)
    assert len(kinds) >= MASTERY_MIN_DISTINCT_EVIDENCE
    assert st.status in (KnowledgeStatus.TRANSFER_CAPABLE, KnowledgeStatus.MASTERED)


def test_self_report_never_exceeds_status_alone():
    """A confident-but-wrong answer does not advance; overconfidence is measurable."""
    st = KnowledgeState(concept_id="c", learner_id=LEARNER)
    ev = _ev("c", EvidenceType.EXPLAIN_OWN_WORDS, "totally unrelated", ["imposed library"],
             confidence=0.95)
    apply_evidence(st, ev)
    assert st.confidence_self_reported >= 0.9
    assert st.confidence_observed < 0.5
    assert overconfidence_gap(st) > 0.4


def test_human_calibration_detects_overconfidence():
    cal = assess_calibration([0.9, 0.9, 0.9, 0.9], [False, False, True, False])
    assert cal.tendency == "overconfident"
    cal2 = assess_calibration([0.5, 0.5], [True, False])
    assert cal2.tendency == "insufficient"      # below min_n


def test_next_review_sooner_for_critical_and_overconfident():
    st = KnowledgeState(concept_id="c", learner_id=LEARNER,
                        status=KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD)
    low = next_review(st, criticality=Criticality.LOW)
    high = next_review(st, criticality=Criticality.BLOCKING, overconfident=True)
    assert high < low                    # earlier ISO timestamp sorts before later


def test_decay_after_review_date():
    st = KnowledgeState(concept_id="c", learner_id=LEARNER,
                        next_review="2000-01-01T00:00:00+00:00")
    assert is_decayed(st)


def test_persistence_round_trip(disc_store):
    store = UnderstandingStore(disc_store)
    st = KnowledgeState(concept_id="c", learner_id=LEARNER,
                        status=KnowledgeStatus.PARTIALLY_UNDERSTOOD)
    store.save_state(st)
    loaded = store.load_state(LEARNER, "c")
    assert loaded is not None
    assert loaded.status == KnowledgeStatus.PARTIALLY_UNDERSTOOD


def test_history_reconstructs_learning(disc_store):
    h = LearningHistory(LEARNER)
    h.record(LearningEvent("transition", "c", "UNKNOWN->MASTERED", "proj",
                           payload={"to": "MASTERED"}))
    assert h.concepts_mastered() == ["c"]
    assert h.summary("proj")["n_events"] == 1
