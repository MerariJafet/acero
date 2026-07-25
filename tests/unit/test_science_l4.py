"""L4: protocol seal levels + substantive DAG validation (offline)."""

from __future__ import annotations

from acero.science.causal import CausalGraph, Estimand
from acero.science.causal_validation import (
    CausalEdge,
    DagValidityLevel,
    EdgeEvidence,
    validate_dag,
)
from acero.science.preregistration import (
    ExternalSeal,
    FrozenAnalysisPlan,
    ProtocolRegistry,
    SealLevel,
)


def _plan():
    return FrozenAnalysisPlan(
        hypothesis="h", primary_variable="v", population="p", inclusion_criteria="i",
        exclusion_criteria="e", variable_transform="t", statistical_model="m",
        primary_test="test", multiplicity_correction="BH", min_effect_size=0.1,
        decision_rule="r", failure_conditions="f")


class _FakeSeal:
    def stamp(self, protocol_hash):
        return ExternalSeal("opentimestamps", "proof:" + protocol_hash[:8],
                            "2026-01-01T00:00:00Z")


# --- seal levels ---------------------------------------------------------
def test_default_seal_is_local_only():
    reg = ProtocolRegistry()
    pre = reg.freeze(_plan())
    assert pre.seal_level is SealLevel.LOCAL_FROZEN and pre.external_seal is None


def test_external_adapter_raises_seal_level():
    reg = ProtocolRegistry()
    pre = reg.freeze(_plan(), seal_adapter=_FakeSeal())
    assert pre.seal_level is SealLevel.EXTERNALLY_TIMESTAMPED
    assert pre.external_seal and pre.external_seal.service == "opentimestamps"
    assert reg.seal_level(pre.hash) is SealLevel.EXTERNALLY_TIMESTAMPED


# --- substantive DAG validation -----------------------------------------
def _confounded_graph():
    g = CausalGraph()
    g.add_edge("C", "X"); g.add_edge("C", "Y"); g.add_edge("X", "Y")
    return g


def test_ai_assumed_dag_is_not_substantive():
    g = _confounded_graph()
    est = Estimand("X", "Y", "u", "p", adjustment_set=("C",))
    edges = [CausalEdge("C", "X"), CausalEdge("C", "Y"), CausalEdge("X", "Y")]  # all ASSUMED
    rep = validate_dag(g, edges, est)
    assert rep.identifiable                       # mathematically identifiable
    assert not rep.substantive_ok                 # but edges unjustified
    assert rep.level is DagValidityLevel.IDENTIFICATION
    assert not rep.allows_causal_language
    assert len(rep.unjustified_edges) == 3


def test_literature_backed_edges_reach_substantive():
    g = _confounded_graph()
    est = Estimand("X", "Y", "u", "p", adjustment_set=("C",))
    edges = [CausalEdge("C", "X", EdgeEvidence.LITERATURE, "doi:1"),
             CausalEdge("C", "Y", EdgeEvidence.EXPERIMENTAL, "exp:2"),
             CausalEdge("X", "Y", EdgeEvidence.LITERATURE, "doi:3")]
    rep = validate_dag(g, edges, est)
    assert rep.substantive_ok and rep.level is DagValidityLevel.SUBSTANTIVE
    assert rep.allows_causal_language


def test_expert_approval_is_top_level():
    g = _confounded_graph()
    est = Estimand("X", "Y", "u", "p", adjustment_set=("C",))
    edges = [CausalEdge("C", "X", EdgeEvidence.EXPERT_APPROVED, approved_by="Dra. X"),
             CausalEdge("C", "Y", EdgeEvidence.EXPERT_APPROVED, approved_by="Dra. X"),
             CausalEdge("X", "Y", EdgeEvidence.EXPERT_APPROVED, approved_by="Dra. X")]
    rep = validate_dag(g, edges, est)
    assert rep.level is DagValidityLevel.EXPERT_APPROVED


def test_unidentifiable_dag_blocks_regardless_of_evidence():
    g = _confounded_graph()
    est = Estimand("X", "Y", "u", "p", adjustment_set=())   # no adjustment → not identifiable
    edges = [CausalEdge("C", "X", EdgeEvidence.LITERATURE),
             CausalEdge("C", "Y", EdgeEvidence.LITERATURE),
             CausalEdge("X", "Y", EdgeEvidence.LITERATURE)]
    rep = validate_dag(g, edges, est)
    assert not rep.identifiable and not rep.allows_causal_language
