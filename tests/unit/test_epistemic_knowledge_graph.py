"""F9: epistemic knowledge graph — typed, versioned, edges never deleted (offline)."""

from __future__ import annotations

from acero.epistemic.knowledge_graph import (
    EpistemicKnowledgeGraph,
    NodeType,
    RelationType,
)


def _g():
    g = EpistemicKnowledgeGraph()
    g.upsert("claim1", NodeType.CLAIM, {"text": "polaridad→permeabilidad"})
    g.upsert("asm1", NodeType.ASSUMPTION, {"text": "sin confusión"})
    g.upsert("ev1", NodeType.EVIDENCE, {"root": "TDC"})
    g.upsert("vul1", NodeType.EPISTEMIC_VULNERABILITY, {"type": "confusion"})
    g.upsert("q1", NodeType.SCIENTIFIC_QUESTION, {"text": "¿confusor?"})
    g.link("claim1", "asm1", RelationType.DEPENDS_ON)
    g.link("ev1", "claim1", RelationType.SUPPORTS)
    g.link("q1", "vul1", RelationType.TARGETS)
    return g


def test_beliefs_are_versioned_never_overwritten():
    g = EpistemicKnowledgeGraph()
    g.upsert("c", NodeType.CLAIM, {"conf": 0.4})
    g.upsert("c", NodeType.CLAIM, {"conf": 0.6})
    node = g.get("c")
    assert node.version == 2 and len(node.history) == 2
    assert node.history[0].data["conf"] == 0.4      # prior belief preserved
    assert node.current["conf"] == 0.6


def test_queries_why_we_believe_and_where_it_fails():
    g = _g()
    assert g.assumptions_of("claim1") == ["asm1"]
    assert g.evidence_for("claim1") == ["ev1"]
    assert g.questions_targeting("vul1") == ["q1"]
    assert g.support_balance("claim1") == 1


def test_edges_are_weakened_not_deleted():
    g = _g()
    g.weaken("ev1", "claim1", RelationType.SUPPORTS)
    assert g.evidence_for("claim1") == []            # no longer active
    # but the edge object still exists (history preserved, not deleted)
    assert any(e.src == "ev1" and not e.active for e in g._edges)


def test_weakening_evidence_flips_support_balance():
    g = _g()
    g.upsert("ev2", NodeType.EVIDENCE, {"root": "ChEMBL"})
    g.link("ev2", "claim1", RelationType.WEAKENS)
    assert g.support_balance("claim1") == 0          # 1 for, 1 against


def test_summary_counts_node_types():
    s = _g().summary()
    assert s["n_nodes"] == 5 and s["by_type"]["claim"] == 1
