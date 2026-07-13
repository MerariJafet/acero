import pytest
from pydantic import ValidationError

from acero.core.errors import WorkflowError
from acero.experiment.prereg import Preregistration, require_complete
from acero.experiment.workflow import ResearchWorkflow, WorkflowState, next_states


def test_workflow_forward_only():
    wf = ResearchWorkflow()
    wf.advance(WorkflowState.BACKGROUND_REVIEWED)
    assert wf.state == WorkflowState.BACKGROUND_REVIEWED


def test_workflow_rejects_skips():
    wf = ResearchWorkflow()
    with pytest.raises(WorkflowError):
        wf.advance(WorkflowState.RUNNING)  # cannot skip to RUNNING


def test_workflow_can_abort_to_closed():
    wf = ResearchWorkflow()
    assert WorkflowState.CLOSED in next_states(wf.state)
    wf.advance(WorkflowState.CLOSED)
    assert wf.state == WorkflowState.CLOSED


def test_require_state():
    wf = ResearchWorkflow()
    with pytest.raises(WorkflowError):
        wf.require(WorkflowState.RUNNING)


def _valid_prereg(**over):
    base = dict(
        project_id="p", experiment_id="e", question="Q?",
        hypotheses=["H1", "H2"], predictions=["P1"],
        metric="RMSE", baseline="mean",
        result_that_would_support="exp wins",
        result_that_would_weaken="poly wins",
        stopping_criterion="one pass",
    )
    base.update(over)
    return Preregistration(**base)


def test_prereg_requires_two_hypotheses():
    with pytest.raises(ValidationError):
        _valid_prereg(hypotheses=["only one"])


def test_prereg_complete_returns_hash():
    pr = _valid_prereg()
    h = require_complete(pr)
    assert h.startswith("sha256:")


def test_prereg_hash_stable_before_and_after_registration_time():
    pr1 = _valid_prereg()
    pr2 = _valid_prereg()
    # registered_at differs but is excluded from the hash
    assert pr1.prereg_hash() == pr2.prereg_hash()


def test_prereg_empty_metric_rejected():
    with pytest.raises(ValidationError):
        _valid_prereg(metric="")
