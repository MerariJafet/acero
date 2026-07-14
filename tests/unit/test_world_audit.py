"""World Model audit + regression tests for the adversarial-audit fixes."""

from __future__ import annotations

import pytest

from acero.world_model.audit import rules_audit
from acero.world_model.edges import EdgeType
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType
from acero.world_model.update import integrate_hidden_dynamics


@pytest.fixture()
def wm(session_factory, ledger, project) -> WorldModel:
    return WorldModel(session_factory, ledger, project.id)


def _report(system="damped_oscillator", winner="damped", hidden="damped"):
    return {"system": system, "hidden_family": hidden, "winner_family": winner,
            "seeds": [1, 2, 3], "eig_bits": 0.8, "reproduced": True,
            "poly9_extrapolation_rmse": 9999.0,
            "family_mean_test_rmse": {"mean": 20.0, "linear": 6.0, "exponential": 3.0,
                                      "damped": 0.5, "poly9": 0.9}}


def test_link_is_idempotent_no_duplicate_edges(wm):
    a = wm.create(NodeType.EVIDENCE, "E")
    b = wm.create(NodeType.CLAIM, "C")
    e1 = wm.link(EdgeType.SUPPORTS, a.id, b.id)
    e2 = wm.link(EdgeType.SUPPORTS, a.id, b.id)  # duplicate
    assert e1.id == e2.id
    assert len(wm.edges(source=a.id, target=b.id, etype=EdgeType.SUPPORTS)) == 1


def test_integration_twice_has_no_redundant_edges(wm):
    integrate_hidden_dynamics(wm, _report())
    integrate_hidden_dynamics(wm, _report(system="damped_oscillator"))
    # No duplicate (source,target,type) edges -> rules audit clean on that concern.
    findings = {f.concern for f in rules_audit(wm).findings}
    assert "redundant_relations" not in findings


def test_all_models_learn_have_history(wm):
    # Audit fix: every model belief is updated, not just the winner.
    out = integrate_hidden_dynamics(wm, _report())
    for family, node_id in out["model_nodes"].items():
        node = wm.get_node(node_id)
        assert node.belief["history"], f"{family} model has no belief history"


def test_invalidated_model_relation_is_weakened(wm):
    # Audit fix: poly9's 'explains' edge is deactivated (weakened), not deleted.
    out = integrate_hidden_dynamics(wm, _report())
    poly9 = out["model_nodes"]["poly9"]
    active = wm.edges(source=poly9, etype=EdgeType.EXPLAINS, active_only=True)
    alle = wm.edges(source=poly9, etype=EdgeType.EXPLAINS, active_only=False)
    assert len(active) == 0 and len(alle) == 1  # weakened, still present


def test_rules_audit_detects_dependency_cycle(wm):
    a = wm.create(NodeType.MODEL, "A")
    b = wm.create(NodeType.MODEL, "B")
    wm.link(EdgeType.DEPENDS_ON, a.id, b.id)
    wm.link(EdgeType.DEPENDS_ON, b.id, a.id)
    concerns = {f.concern for f in rules_audit(wm).findings}
    assert "dependency_cycle" in concerns


def test_rules_audit_learns(wm):
    integrate_hidden_dynamics(wm, _report())
    concerns = {f.concern for f in rules_audit(wm).findings}
    assert "does_not_learn" not in concerns  # beliefs changed → it learns
