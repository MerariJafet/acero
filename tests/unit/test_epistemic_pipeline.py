"""F8: epistemic pipeline topic→discriminating test→ready (offline)."""

from __future__ import annotations

from acero.epistemic.claim_reconstructor import ClaimRecord, EvidenceType, ReplicationStatus
from acero.epistemic.pipeline import run_pipeline
from acero.science.pre_research_states import PreResearchState


def _claim(cid):
    return ClaimRecord(
        claim_id=cid, claim_text=f"{cid}: X→Y", exposure_or_input="polaridad",
        outcome_or_prediction="permeabilidad", effect_direction="neg",
        evidence_type=EvidenceType.OBSERVATIONAL, provenance_roots=("TDC",),
        replication_status=ReplicationStatus.INTERNAL_ONLY)


def test_pipeline_reaches_ready_for_exploratory():
    res = run_pipeline("permeabilidad Caco-2", [_claim("c1")],
                       confounder_candidates=("peso", "lipofilia"))
    assert res.ready_for_exploratory
    assert res.state is PreResearchState.READY_FOR_EXPLORATORY_RESEARCH
    assert res.discriminating_test and res.discriminating_test.decisive


def test_pipeline_without_claims_does_not_reach_ready():
    res = run_pipeline("tema vacío", [])
    assert not res.ready_for_exploratory
    assert res.state is PreResearchState.TOPIC_RECEIVED


def test_pipeline_records_semantic_exploration():
    res = run_pipeline("permeabilidad", [_claim("c1")])
    assert res.semantic.summary()["n_events"] >= 1     # questions considered logged


def test_pipeline_summary_has_information_bits():
    res = run_pipeline("permeabilidad", [_claim("c1")],
                       confounder_candidates=("peso",))
    s = res.summary()
    assert s["discriminating_test_bits"] and s["ready_for_exploratory"]
