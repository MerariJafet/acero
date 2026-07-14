"""Sprint 10 tests: the hybrid understanding grader."""

from __future__ import annotations

from acero.understanding.grading.aggregation import (
    GradeVerdict,
    grade_hybrid,
)
from acero.understanding.grading.audit import run as audit_run
from acero.understanding.grading.calibration import run as cal_run

Q = "Explain why recovering an equation from data is not discovering a law."
EXPECTED = ["imposed library", "fit", "not a law", "system identification"]
FORBIDDEN = ["discovered a law of nature", "proves the mechanism"]


class _MockSemantic:
    """Codex stand-in that recognizes a valid paraphrase (cited fragment must be real)."""

    def __init__(self, valid: bool = True, fragment: str = "") -> None:
        self.valid = valid
        self.fragment = fragment

    def complete_json(self, prompt, schema, *, temperature=0.0):
        v = 0.9 if self.valid else 0.2
        return {"paraphrase_validity": v, "conceptual_coherence": v,
                "missing_nuance": [], "circular_reasoning": False,
                "contradiction": False, "unsupported_claim": not self.valid,
                "transfer_quality": v, "suggested_low": 0.6, "suggested_high": 0.9,
                "rationale": "mock", "cited_fragments": [self.fragment] if self.fragment else []}


def test_literal_correct_passes():
    g = grade_hybrid(Q, "The recovered term came from an imposed library and was chosen by "
                     "its fit, so this is system identification, not a law.", EXPECTED,
                     forbidden_elements=FORBIDDEN)
    assert g.verdict == GradeVerdict.PASS
    assert g.can_reach_mastery


def test_keyword_echo_fails():
    g = grade_hybrid(Q, "imposed library fit not a law system identification", EXPECTED,
                     forbidden_elements=FORBIDDEN)
    assert g.verdict == GradeVerdict.HARD_FAIL
    assert not g.can_reach_mastery


def test_prohibited_claim_hard_fails():
    g = grade_hybrid(Q, "we recovered the equation from data so it is a discovered law",
                     EXPECTED, forbidden_elements=FORBIDDEN)
    assert g.verdict == GradeVerdict.HARD_FAIL
    assert g.prohibited


def test_self_contradiction_hard_fails():
    g = grade_hybrid(Q, "it is causal and it is not causal at the same time", EXPECTED)
    assert g.verdict == GradeVerdict.HARD_FAIL


def test_semantic_unavailable_falls_back_to_deterministic():
    g = grade_hybrid(Q, "The imposed library was chosen by us; the fit is not a law and "
                     "this is system identification.", EXPECTED, forbidden_elements=FORBIDDEN,
                     provider=None)
    assert not g.semantic_available
    assert g.verdict in (GradeVerdict.PASS,)


def test_valid_paraphrase_recognized_with_semantic():
    para = ("We picked a catalogue of candidate terms ourselves and kept the ones that "
            "matched the data best; matching data is not the same as finding a natural law.")
    g = grade_hybrid(Q, para, EXPECTED, forbidden_elements=FORBIDDEN,
                     provider=_MockSemantic(valid=True, fragment="catalogue of candidate terms"))
    assert g.verdict == GradeVerdict.PASS_WITH_REVIEW
    assert g.disagreement


def test_codex_never_unlocks_mastery():
    """Even a maximally lenient semantic layer cannot grant mastery to a weak answer."""
    weak = "it depends on the model somehow"
    g = grade_hybrid(Q, weak, EXPECTED, forbidden_elements=FORBIDDEN,
                     provider=_MockSemantic(valid=True, fragment="it depends on the model"))
    assert not g.can_reach_mastery


def test_disagreement_is_recorded():
    g = grade_hybrid(Q, "The imposed library was chosen by us; the fit is not a law, this "
                     "is system identification.", EXPECTED, forbidden_elements=FORBIDDEN,
                     provider=_MockSemantic(valid=False))
    # deterministic PASS but semantic concern → recorded disagreement, PASS_WITH_REVIEW
    assert g.disagreement
    assert g.verdict == GradeVerdict.PASS_WITH_REVIEW


def test_repeat_of_prior_answer_flagged():
    prior = ["the imposed library was chosen by us so the fit is not a law and this is "
             "system identification"]
    g = grade_hybrid(Q, prior[0], EXPECTED, forbidden_elements=FORBIDDEN,
                     prior_responses=prior)
    assert g.verdict == GradeVerdict.PASS_WITH_REVIEW      # low originality


def test_calibration_no_false_positives():
    c = cal_run()
    assert c.false_positives == 0
    assert c.agreement >= 0.8


def test_adversarial_audit_not_fooled():
    a = audit_run()
    assert not a.any_fooled


def test_adversarial_audit_not_fooled_even_with_lenient_semantic():
    a = audit_run(provider=_MockSemantic(valid=True))
    assert not a.any_fooled


# --- Codex-audit regression fixes (Sprint 10) -----------------------------

def test_semantic_lift_requires_a_cited_fragment():
    """A strong semantic signal with NO cited fragment cannot lift the grade."""
    para = ("We picked a catalogue of candidate terms ourselves and kept the ones that "
            "matched the data best; matching data is not the same as finding a natural law.")
    no_cite = _MockSemantic(valid=True, fragment="")           # no fragment cited
    g = grade_hybrid(Q, para, EXPECTED, forbidden_elements=FORBIDDEN, provider=no_cite)
    assert g.verdict != GradeVerdict.PASS_WITH_REVIEW          # not lifted without a cite
    with_cite = _MockSemantic(valid=True, fragment="catalogue of candidate terms")
    g2 = grade_hybrid(Q, para, EXPECTED, forbidden_elements=FORBIDDEN, provider=with_cite)
    assert g2.verdict == GradeVerdict.PASS_WITH_REVIEW         # lifted WITH a real cite
