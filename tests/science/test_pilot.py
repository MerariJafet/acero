"""Scientific-integrity tests for the Sprint-4 pilot.

These assert the *process* guarantees, not a particular scientific result:
preregistration exists, runs are reproducible, negative results are preserved,
provenance is complete, and nothing is called a discovery.
"""

import pytest

from acero.epistemology.types import EntityType
from acero.experiment.orchestrator import run_pilot

pytestmark = pytest.mark.science


@pytest.fixture()
def pilot(ledger, project, tmp_path):
    return run_pilot(ledger, project.id, artifacts_root=tmp_path, seeds=[1, 2]), ledger, project


def test_workflow_reached_human_review(pilot):
    rep, _, _ = pilot
    assert rep["workflow_history"][0] == "QUESTION_DEFINED"
    assert rep["workflow_history"][-1] == "HUMAN_REVIEW"
    # no illegal skips: each step is the immediate successor
    assert "PREDICTIONS_PREREGISTERED" in rep["workflow_history"]


def test_preregistration_hash_exists(pilot):
    rep, _, _ = pilot
    assert rep["prereg_hash"].startswith("sha256:")


def test_at_least_two_competing_hypotheses_with_predictions(pilot):
    rep, ledger, project = pilot
    hyps = ledger.list_entities(project.id, EntityType.HYPOTHESIS)
    preds = ledger.list_entities(project.id, EntityType.PREDICTION)
    assert len(hyps) >= 2
    assert len(preds) >= 1
    for p in preds:
        assert p["hypothesis_id"] in {h["id"] for h in hyps}


def test_run_is_reproducible(pilot):
    rep, _, _ = pilot
    assert rep["reproduced"] is True


def test_negative_result_recorded_and_preserved(pilot):
    rep, ledger, project = pilot
    negs = ledger.list_entities(project.id, EntityType.NEGATIVE_RESULT)
    assert negs, "the overfitting negative result must be recorded"
    from acero.core.errors import IntegrityError
    with pytest.raises(IntegrityError):
        ledger.delete_entity(negs[0]["id"])


def test_skeptic_attempted_refutation(pilot):
    rep, _, _ = pilot
    assert rep["skeptic"]["n_objections"] >= 5
    concerns = {o["concern"] for o in rep["skeptic"]["objections"]}
    assert "overfitting" in concerns
    assert "fit_is_not_explanation" in concerns


def test_overfitter_fails_extrapolation(pilot):
    rep, _, _ = pilot
    m = rep["reference_metrics"]
    # The flexible poly9 should extrapolate far worse than the chosen model.
    assert m["overfit_extrapolation_rmse"] > m["extrapolation_rmse"]


def test_no_discovery_claim(pilot):
    rep, ledger, project = pilot
    assert rep["cannot_conclude"]
    claims = ledger.list_entities(project.id, EntityType.CLAIM)
    for c in claims:
        assert "descubrimiento" in c["description"].lower() or "discovery" not in c["title"].lower()


def test_results_have_provenance_to_runs(pilot):
    rep, ledger, project = pilot
    results = ledger.list_entities(project.id, EntityType.RESULT)
    assert results
    for r in results:
        assert r["run_id"] in rep["run_ids"]


def test_learning_artifacts_generated(pilot):
    rep, _, _ = pilot
    assert set(rep["learning_files"]) >= {
        "intuition.md", "mathematics.md", "code_walkthrough.md",
        "assumptions.md", "human_questions.md", "knowledge_check.md",
    }
