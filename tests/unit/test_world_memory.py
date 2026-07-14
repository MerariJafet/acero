"""Scientific memory queries, programs, evolution, and narration."""

from __future__ import annotations

import pytest

from acero.world_model.edges import EdgeType
from acero.world_model.evolution import evolution_report, snapshot
from acero.world_model.graph import WorldModel
from acero.world_model.narrate import narrate
from acero.world_model.nodes import NodeType
from acero.world_model.programs import attach, create_program, program_summary
from acero.world_model.queries import ScientificMemory


@pytest.fixture()
def wm(session_factory, ledger, project) -> WorldModel:
    return WorldModel(session_factory, ledger, project.id)


def test_supporting_and_contradicting(wm):
    claim = wm.create(NodeType.CLAIM, "C")
    exp = wm.create(NodeType.EXPERIMENT, "E1")
    counter = wm.create(NodeType.COUNTER_EVIDENCE, "CE")
    wm.link(EdgeType.SUPPORTS, exp.id, claim.id)
    wm.link(EdgeType.CONTRADICTS, counter.id, claim.id)
    mem = ScientificMemory(wm)
    assert [n.id for n in mem.supporting_experiments(claim.id)] == [exp.id]
    assert [n.id for n in mem.contradicting_evidence(claim.id)] == [counter.id]


def test_models_depending_on_untested_assumption(wm):
    a = wm.create(NodeType.ASSUMPTION, "Isotropy")  # tested=False by default
    m = wm.create(NodeType.MODEL, "Cosmology model")
    wm.link(EdgeType.DEPENDS_ON, m.id, a.id)
    mem = ScientificMemory(wm)
    assert [n.id for n in mem.models_depending_on(a.id)] == [m.id]
    crit = mem.critical_assumptions()
    assert crit and crit[0]["assumption"] == "Isotropy"


def test_untested_and_single_source(wm):
    h = wm.create(NodeType.HYPOTHESIS, "Untested H")
    mem = ScientificMemory(wm)
    assert h.id in {n.id for n in mem.untested_beliefs()}
    # single source: one evidence update
    c = wm.create(NodeType.CLAIM, "Single-source claim")
    wm.update_belief(c.id, event="experiment", evidence=1.0, source="one_paper")
    assert c.id in {n.id for n in mem.single_source_claims()}


def test_weak_relations(wm):
    a = wm.create(NodeType.EVIDENCE, "E")
    b = wm.create(NodeType.CLAIM, "C")
    wm.link(EdgeType.SUPPORTS, a.id, b.id, weight=0.1, confidence=0.2)
    weak = ScientificMemory(wm).weak_relations(threshold=0.3)
    assert weak and weak[0]["strength"] < 0.3


def test_program_summary(wm):
    prog = create_program(wm, "Dark Matter Program")
    h = wm.create(NodeType.HYPOTHESIS, "WIMP hypothesis")
    attach(wm, prog.id, h.id)
    summ = program_summary(wm, prog.id)
    assert summ["n_members"] == 1
    assert summ["members_by_type"]["Hypothesis"] == 1


def test_evolution_report_shows_believe_more(wm):
    claim = wm.create(NodeType.CLAIM, "Gains support")
    exp = wm.create(NodeType.EXPERIMENT, "E1")
    wm.link(EdgeType.SUPPORTS, exp.id, claim.id)
    before = snapshot(wm)
    # three independent experiments favour the claim
    for i in range(3):
        wm.update_belief(claim.id, event="experiment", evidence=1.0, replication=1,
                         source=f"exp{i}")
    after = snapshot(wm)
    evo = evolution_report(wm, before, after)
    assert any(e["id"] == claim.id for e in evo["believe_more"])


def test_narrate_gained_support(wm):
    claim = wm.create(NodeType.CLAIM, "Replicated claim")
    exp = wm.create(NodeType.EXPERIMENT, "E1")
    wm.link(EdgeType.SUPPORTS, exp.id, claim.id)
    for i in range(3):
        wm.update_belief(claim.id, event="experiment", evidence=1.5, replication=1,
                         source=f"exp{i}")
    statements = narrate(wm)
    kinds = {s["kind"] for s in statements}
    assert "gained_support" in kinds


def test_narrate_critical_assumption(wm):
    a = wm.create(NodeType.ASSUMPTION, "Homogeneity")
    m = wm.create(NodeType.THEORY, "Standard model of cosmology")
    wm.link(EdgeType.DEPENDS_ON, m.id, a.id)
    statements = narrate(wm)
    assert any(s["kind"] == "critical_untested_assumption" for s in statements)
