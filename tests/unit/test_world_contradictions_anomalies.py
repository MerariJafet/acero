"""Contradiction and anomaly engines."""

from __future__ import annotations

import pytest

from acero.world_model.anomalies import register_anomaly, resolve_anomaly
from acero.world_model.contradictions import detect_contradictions, resolve_contradiction
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType
from acero.world_model.queries import ScientificMemory


@pytest.fixture()
def wm(session_factory, ledger, project) -> WorldModel:
    return WorldModel(session_factory, ledger, project.id)


def test_detects_incompatible_beliefs_and_opens_question(wm):
    wm.create(NodeType.MODEL, "M-inc", data={"subject": "gravity", "stance": "increases"})
    wm.create(NodeType.MODEL, "M-dec", data={"subject": "gravity", "stance": "decreases"})
    created = detect_contradictions(wm)
    assert len(created) == 1
    # a Contradiction node and a Question were created
    assert wm.nodes(NodeType.CONTRADICTION)
    assert wm.nodes(NodeType.QUESTION)


def test_contradiction_penalises_both_beliefs(wm):
    a = wm.create(NodeType.MODEL, "A", data={"subject": "x", "stance": "exists"})
    b = wm.create(NodeType.MODEL, "B", data={"subject": "x", "stance": "not_exists"})
    wm.update_belief(a.id, event="experiment", evidence=2.0, source="s")
    before = wm.get_node(a.id).confidence
    detect_contradictions(wm)
    assert wm.get_node(a.id).confidence < before
    assert wm.get_node(b.id).belief["contradictions"] == 1


def test_detection_is_idempotent(wm):
    wm.create(NodeType.MODEL, "A", data={"subject": "x", "stance": "linear"})
    wm.create(NodeType.MODEL, "B", data={"subject": "x", "stance": "exponential"})
    first = detect_contradictions(wm)
    second = detect_contradictions(wm)
    assert len(first) == 1 and len(second) == 0


def test_compatible_stances_no_contradiction(wm):
    wm.create(NodeType.MODEL, "A", data={"subject": "x", "stance": "linear"})
    wm.create(NodeType.MODEL, "B", data={"subject": "x", "stance": "linear"})
    assert detect_contradictions(wm) == []


def test_resolve_contradiction(wm):
    wm.create(NodeType.MODEL, "A", data={"subject": "x", "stance": "holds"})
    wm.create(NodeType.MODEL, "B", data={"subject": "x", "stance": "violated"})
    detect_contradictions(wm)
    con = wm.nodes(NodeType.CONTRADICTION)[0]
    resolve_contradiction(wm, con.id, "measurement error in one study")
    assert wm.get_node(con.id).data["resolved"] is True
    assert not ScientificMemory(wm).open_contradictions()


def test_anomaly_registered_with_candidates_and_open_problem(wm):
    exp = wm.create(NodeType.EXPERIMENT, "exp1")
    a = register_anomaly(wm, label="Unexpected oscillation", expected="monotonic decay",
                         observed="oscillation", experiment_id=exp.id,
                         candidate_explanations=["hidden periodic forcing", "instrument artefact"])
    assert a.data["resolved"] is False
    assert a.data["expected"] == "monotonic decay"
    # candidate explanations became hypotheses; an open problem was opened
    assert len(wm.nodes(NodeType.HYPOTHESIS)) == 2
    assert wm.nodes(NodeType.OPEN_PROBLEM)


def test_anomaly_persists_until_resolved(wm):
    a = register_anomaly(wm, label="A", expected=1, observed=2)
    mem = ScientificMemory(wm)
    assert len(mem.open_anomalies()) == 1
    resolve_anomaly(wm, a.id, "explained by systematic offset")
    assert len(mem.open_anomalies()) == 0
