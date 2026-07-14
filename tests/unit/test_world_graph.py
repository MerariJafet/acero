"""World Model graph: nodes, edges, versioning, persistence."""

from __future__ import annotations

import pytest

from acero.core.errors import IntegrityError
from acero.world_model.edges import EdgeType
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType


@pytest.fixture()
def wm(session_factory, ledger, project) -> WorldModel:
    return WorldModel(session_factory, ledger, project.id)


def test_create_and_get_node(wm):
    n = wm.create(NodeType.CLAIM, "Dark matter exists")
    got = wm.get_node(n.id)
    assert got is not None and got.label == "Dark matter exists"
    assert got.is_belief


def test_persistence_survives_new_instance(session_factory, ledger, project):
    wm1 = WorldModel(session_factory, ledger, project.id)
    n = wm1.create(NodeType.LAW, "Inverse square gravity")
    wm2 = WorldModel(session_factory, ledger, project.id)
    assert wm2.get_node(n.id) is not None
    assert len(wm2.nodes()) == 1


def test_get_or_create_is_idempotent(wm):
    a = wm.get_or_create(NodeType.CONCEPT, "Gravity")
    b = wm.get_or_create(NodeType.CONCEPT, "gravity")  # case-insensitive
    assert a.id == b.id


def test_belief_update_is_versioned_and_provenance_recorded(wm, ledger, project):
    n = wm.create(NodeType.HYPOTHESIS, "H1")
    before = n.confidence
    wm.update_belief(n.id, event="experiment", evidence=1.0, source="exp1")
    after = wm.get_node(n.id)
    assert after.confidence != before
    assert after.version >= 2
    hist = wm.node_history(n.id)
    assert len(hist) >= 2  # create + update
    actions = {p["action"] for p in ledger.provenance_for_project(project.id)}
    assert "CONFIDENCE_UPDATE" in actions


def test_edges_require_existing_nodes(wm):
    n = wm.create(NodeType.CLAIM, "C")
    with pytest.raises(IntegrityError):
        wm.link(EdgeType.SUPPORTS, "missing", n.id)


def test_edge_reweight_and_deactivate_is_not_deletion(wm):
    a = wm.create(NodeType.EVIDENCE, "E")
    b = wm.create(NodeType.CLAIM, "C")
    e = wm.link(EdgeType.SUPPORTS, a.id, b.id, weight=1.0)
    wm.reweight_edge(e.id, weight=0.1, deactivate=True)
    active = wm.edges(active_only=True)
    alle = wm.edges(active_only=False)
    assert len(active) == 0 and len(alle) == 1  # weakened, not deleted


def test_stats_counts_types(wm):
    wm.create(NodeType.CLAIM, "C1")
    wm.create(NodeType.CLAIM, "C2")
    wm.create(NodeType.EXPERIMENT, "E1")
    s = wm.stats()
    assert s["nodes_by_type"]["Claim"] == 2
    assert s["n_nodes"] == 3


def test_duplicate_node_id_rejected(wm):
    from acero.world_model.nodes import make_node
    n = wm.create(NodeType.CLAIM, "X")
    dup = make_node(project_id=wm.project_id, ntype=NodeType.CLAIM, label="Y")
    dup.id = n.id
    with pytest.raises(IntegrityError):
        wm.add_node(dup)
