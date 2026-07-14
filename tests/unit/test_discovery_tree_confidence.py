"""Sprint 7 tests: research tree persistence, pruning, and confidence updates."""

from __future__ import annotations

import pytest

from acero.core.errors import IntegrityError
from acero.discovery.confidence import (
    ConfidenceLevel,
    assess_result_quality,
    bayesian_update,
    ordinal_update,
    which_weakens,
)
from acero.discovery.tree import NodeStatus, ResearchTree, TreeNode


def test_tree_persists_and_survives_new_instance(disc_store, project):
    tree = ResearchTree(disc_store, project.id)
    root = tree.add(TreeNode(project_id=project.id, kind="question", title="Q"))
    child = tree.add(TreeNode(project_id=project.id, kind="hypothesis", title="H",
                              parent_id=root.id))
    # A fresh tree object over the same store sees the persisted nodes (restart).
    tree2 = ResearchTree(disc_store, project.id)
    assert len(tree2.all_nodes()) == 2
    assert [n.id for n in tree2.children(root.id)] == [child.id]


def test_tree_prune_is_explainable_and_recorded(disc_store, project, ledger):
    tree = ResearchTree(disc_store, project.id)
    n = tree.add(TreeNode(project_id=project.id, kind="experiment", title="E"))
    tree.prune(n.id, reason="dominated by cheaper discriminating test")
    pruned = tree.get(n.id)
    assert pruned.status == NodeStatus.PRUNED
    assert "dominated" in pruned.prune_reason
    assert "PRUNE" in {p["action"] for p in ledger.provenance_for_project(project.id)}


def test_tree_frontier_lists_runnable_experiments(disc_store, project):
    tree = ResearchTree(disc_store, project.id)
    tree.add(TreeNode(project_id=project.id, kind="experiment", title="run me",
                      status=NodeStatus.VALIDATED))
    tree.add(TreeNode(project_id=project.id, kind="experiment", title="done",
                      status=NodeStatus.COMPLETED))
    assert len(tree.frontier()) == 1


def test_bayesian_update_shifts_toward_evidence():
    prior = {"a": 0.5, "b": 0.5}
    # observed outcome much more likely under 'a'
    post = bayesian_update(prior, {"a": 0.9, "b": 0.1}).posterior
    assert post["a"] > post["b"]
    assert abs(sum(post.values()) - 1.0) < 1e-9


def test_bayesian_update_uninformative_keeps_prior():
    prior = {"a": 0.5, "b": 0.5}
    post = bayesian_update(prior, {"a": 0.0, "b": 0.0}).posterior
    assert abs(post["a"] - 0.5) < 1e-9


def test_ordinal_update_bounded_and_labelled():
    q = assess_result_quality({"reproduced": True, "discriminating": True, "status": "ok"})
    up = ordinal_update("h", ConfidenceLevel.NEUTRAL, "supported", q)
    assert up.method == "ordinal"
    assert up.updated == ConfidenceLevel.SUPPORTED
    # refuted with trustworthy result -> REFUTED
    down = ordinal_update("h", ConfidenceLevel.SUPPORTED, "refuted", q)
    assert down.updated == ConfidenceLevel.REFUTED


def test_low_quality_result_moves_confidence_less():
    poor = assess_result_quality({"reproduced": False, "discriminating": False, "status": "failed"})
    up = ordinal_update("h", ConfidenceLevel.NEUTRAL, "supported", poor)
    assert up.updated == ConfidenceLevel.NEUTRAL  # no change on untrustworthy result


def test_inconclusive_no_change():
    q = assess_result_quality({"reproduced": True, "status": "ok"})
    up = ordinal_update("h", ConfidenceLevel.SUPPORTED, "inconclusive", q)
    assert up.updated == ConfidenceLevel.SUPPORTED


def test_which_weakens_returns_below_mean():
    assert which_weakens({"a": 0.7, "b": 0.2, "c": 0.1}) == ["b", "c"]


def test_negative_store_delete_blocked(disc_store, project):
    disc_store.put(project.id, "negative", "neg1", {"summary": "x"}, status="RECORDED")
    with pytest.raises(IntegrityError):
        disc_store.delete("neg1")
