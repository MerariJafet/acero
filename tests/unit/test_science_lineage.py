"""L3: semantic exploration ledger + hypothesis lineage (anti-HARKing, offline)."""

from __future__ import annotations

from acero.science.lineage import (
    HypothesisLineageGraph,
    SemanticEventKind,
    SemanticExplorationLedger,
)


def test_reframe_after_results_is_harking():
    lg = SemanticExplorationLedger()
    lg.question("¿la polaridad predice permeabilidad?")     # before results
    lg.mark_results_seen()
    lg.reframe("en realidad buscábamos el efecto del peso molecular")  # HARKing
    flags = lg.harking_flags()
    assert len(flags) == 1 and flags[0].kind is SemanticEventKind.HYPOTHESIS_REFRAME
    ok, why = lg.confirmatory_allowed(has_new_independent_evidence=False)
    assert not ok and "HARKing" in why


def test_harking_cleared_by_new_independent_evidence():
    lg = SemanticExplorationLedger()
    lg.mark_results_seen()
    lg.change_endpoint("cambiar a un endpoint distinto tras ver la señal")
    assert not lg.confirmatory_allowed(False)[0]
    assert lg.confirmatory_allowed(has_new_independent_evidence=True)[0]


def test_changes_before_results_are_not_harking():
    lg = SemanticExplorationLedger()
    lg.change_endpoint("elegir endpoint")     # before mark_results_seen → not HARKing
    lg.reframe("afinar hipótesis")
    assert lg.harking_flags() == []
    assert lg.confirmatory_allowed()[0]


def test_semantic_forks_counted():
    lg = SemanticExplorationLedger()
    lg.question("q1"); lg.question("q2")
    lg.discard_hypothesis("h1")
    lg.reject_dataset("d1")
    assert lg.semantic_forks() == 4
    assert lg.summary()["semantic_forks"] == 4


def test_lineage_trace_reconstructs_path():
    g = HypothesisLineageGraph()
    g.add("idea", "algo con moléculas", "idea")
    g.add("refined", "polaridad vs permeabilidad", "refined")
    g.add("final", "polaridad predice permeabilidad", "final")
    g.link("idea", "refined", "acotar")
    g.link("refined", "final", "operacionalizar")
    chain = g.trace("final")
    assert [n.id for n in chain] == ["idea", "refined", "final"]
    assert not g.final_reframed_after_results("final")


def test_lineage_flags_post_result_reframe():
    g = HypothesisLineageGraph()
    g.add("idea", "idea inicial", "idea")
    g.add("final", "hipótesis reformulada tras ver datos", "final", after_results=True)
    g.link("idea", "final", "reframe")
    assert g.final_reframed_after_results("final")
