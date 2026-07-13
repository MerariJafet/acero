import pytest

from acero.core.errors import IntegrityError, WorkflowError
from acero.core.ids import new_id
from acero.epistemology.schemas import (
    Evidence,
    ExecutionRun,
    Hypothesis,
    NegativeResult,
    Prediction,
    ResearchQuestion,
    ScientificClaim,
)
from acero.epistemology.types import EntityState


def _question(ledger, project):
    q = ResearchQuestion(id=new_id("q"), project_id=project.id, title="Why?")
    return ledger.add_entity(q)


def test_hypothesis_requires_existing_question(ledger, project):
    h = Hypothesis(id=new_id("hyp"), project_id=project.id, question_id="q_missing", title="H")
    with pytest.raises(IntegrityError):
        ledger.add_entity(h)


def test_prediction_requires_existing_hypothesis(ledger, project):
    p = Prediction(id=new_id("pred"), project_id=project.id, hypothesis_id="hyp_missing", title="P")
    with pytest.raises(IntegrityError):
        ledger.add_entity(p)


def test_full_chain_ok(ledger, project):
    q = _question(ledger, project)
    h = ledger.add_entity(Hypothesis(id=new_id("hyp"), project_id=project.id,
                                     question_id=q.id, title="H1"))
    p = ledger.add_entity(Prediction(id=new_id("pred"), project_id=project.id,
                                     hypothesis_id=h.id, title="P1"))
    assert ledger.get_entity(p.id)["hypothesis_id"] == h.id


def test_result_requires_run(ledger, project):
    from acero.epistemology.schemas import ResearchResult

    r = ResearchResult(id=new_id("res"), project_id=project.id, run_id="run_missing", title="R")
    with pytest.raises(IntegrityError):
        ledger.add_entity(r)


def test_claim_requires_support_or_speculation_flag(ledger, project):
    c = ScientificClaim(id=new_id("clm"), project_id=project.id, title="bold claim")
    with pytest.raises(IntegrityError):
        ledger.add_entity(c)  # no support, not flagged speculation
    c2 = ScientificClaim(id=new_id("clm"), project_id=project.id, title="spec", is_speculation=True)
    ledger.add_entity(c2)  # allowed as speculation


def test_evidence_requires_provenance():
    with pytest.raises(ValueError):
        Evidence(id=new_id("ev"), project_id="p", title="e", provenance=[])


def test_negative_result_cannot_be_deleted(ledger, project):
    run = ExecutionRun(id=new_id("run"), project_id=project.id, experiment_id="exp")
    ledger.add_run(run)
    neg = ledger.add_entity(NegativeResult(id=new_id("neg"), project_id=project.id,
                                           run_id=run.id, title="null result"))
    with pytest.raises(IntegrityError):
        ledger.delete_entity(neg.id)


def test_illegal_state_transition_rejected(ledger, project):
    q = _question(ledger, project)
    with pytest.raises(WorkflowError):
        ledger.transition_state(q.id, EntityState.SUPPORTED)  # DRAFT -> SUPPORTED skip


def test_history_and_provenance_recorded(ledger, project):
    q = _question(ledger, project)
    ledger.transition_state(q.id, EntityState.PROPOSED)
    ledger.update_entity(q.id, {"description": "clarified"})
    hist = ledger.history_for_entity(q.id)
    assert len(hist) >= 3  # create + transition + update
    prov = ledger.provenance_for_project(project.id)
    actions = {p["action"] for p in prov}
    assert "CREATE" in actions and "STATE_CHANGE" in actions and "UPDATE" in actions


def test_harking_guard_flags_post_result_hypothesis_edit(ledger, project):
    q = _question(ledger, project)
    h = ledger.add_entity(Hypothesis(id=new_id("hyp"), project_id=project.id,
                                     question_id=q.id, title="H"))
    run = ledger.add_run(ExecutionRun(id=new_id("run"), project_id=project.id, experiment_id="e"))
    from acero.epistemology.schemas import ResearchResult
    ledger.add_entity(ResearchResult(id=new_id("res"), project_id=project.id,
                                     run_id=run.id, title="R"))
    ledger.update_entity(h.id, {"title": "H edited after results"})
    prov = ledger.provenance_for_project(project.id)
    flags = [p for p in prov if p.get("details", {}).get("flag") == "post_result_hypothesis_edit"]
    assert flags, "HARKing edit should be flagged in provenance"


def test_add_entity_to_missing_project_fails(ledger):
    q = ResearchQuestion(id=new_id("q"), project_id="proj_missing", title="Q")
    with pytest.raises(IntegrityError):
        ledger.add_entity(q)
