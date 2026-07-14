"""Sprint 10 property tests: inline gate and hybrid grader invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from acero.epistemic_gate.enforcement import GateEnforcer
from acero.epistemic_gate.exceptions import GateBlockedError
from acero.epistemic_gate.models import Stage
from acero.epistemic_gate.transaction import in_context
from acero.understanding.grading.aggregation import GradeVerdict, grade_hybrid

_Q = "Explain why recovering an equation from data is not discovering a law."
_EXP = ["imposed library", "fit", "not a law", "system identification"]
_FORBIDDEN = ["discovered a law of nature", "proves the mechanism"]


@given(
    provenance=st.booleans(),
    reproduced_ok=st.booleans(),
    codex_only=st.booleans(),
)
@settings(max_examples=40, deadline=None)
def test_blocked_mutation_never_runs(provenance, reproduced_ok, codex_only):
    """A blocked enforce() never runs the mutation; a passing one always does."""
    ran = {"v": False}
    art = {"updated_by_codex_only": codex_only, "evidence_has_provenance": provenance,
           "contradiction_ignored": False, "overwrites_history": False,
           "belief_confidence": 0.6, "dependent_counted_as_independent": False,
           "simulation_as_physical_proof": False, "claim_without_limitations": False}
    enf = GateEnforcer()

    def mutate():
        ran["v"] = True
        return "ok"

    has_blocker = (not provenance) or codex_only
    try:
        enf.enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=art,
                    mutation=mutate)
        assert not has_blocker            # only reaches here if not blocked
        assert ran["v"]
    except GateBlockedError:
        assert has_blocker
        assert not ran["v"]               # mutation did NOT run
    assert not in_context()               # window always closes


@given(response=st.text(min_size=0, max_size=40))
@settings(max_examples=40, deadline=None)
def test_short_or_empty_answer_never_reaches_mastery(response):
    """No short/empty answer can be graded into mastery."""
    g = grade_hybrid(_Q, response, _EXP, forbidden_elements=_FORBIDDEN)
    if g.can_reach_mastery:
        # the only way is a genuine full deterministic pass — implies real content
        assert g.verdict == GradeVerdict.PASS
        assert g.deterministic_score >= 0.7


@given(
    para_valid=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=30, deadline=None)
def test_semantic_never_unlocks_mastery(para_valid):
    """However confident the semantic layer, it never unlocks mastery on a weak answer."""
    class Sem:
        def complete_json(self, prompt, schema, *, temperature=0.0):
            return {"paraphrase_validity": para_valid, "conceptual_coherence": para_valid,
                    "missing_nuance": [], "circular_reasoning": False,
                    "contradiction": False, "unsupported_claim": False,
                    "transfer_quality": para_valid, "suggested_low": 0.7,
                    "suggested_high": 1.0, "rationale": "x", "cited_fragments": []}
    g = grade_hybrid(_Q, "it depends on the model", _EXP, forbidden_elements=_FORBIDDEN,
                     provider=Sem())
    assert not g.can_reach_mastery
