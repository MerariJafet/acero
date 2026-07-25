"""F4: knowledge landscape + diversified question portfolio (offline)."""

from __future__ import annotations

from acero.epistemic.claim_reconstructor import ClaimRecord, EvidenceType, ReplicationStatus
from acero.epistemic.vulnerability import scan_vulnerabilities
from acero.questions.knowledge_landscape import KnowledgeLandscape
from acero.questions.portfolio import build_portfolio, family_coverage
from acero.questions.question_engine import generate_portfolio


def _claim(cid, **over):
    base = dict(claim_id=cid, claim_text=cid, exposure_or_input="X",
                outcome_or_prediction="Y", effect_direction="pos",
                evidence_type=EvidenceType.OBSERVATIONAL, provenance_roots=("R",),
                replication_status=ReplicationStatus.INTERNAL_ONLY)
    base.update(over)
    return ClaimRecord(**base)


def test_landscape_aggregates_gaps_across_claims():
    land = KnowledgeLandscape("permeabilidad")
    land.add_claim(_claim("c1"))
    land.add_claim(_claim("c2", contradicting_sources=("paperX",)))
    s = land.summary()
    assert s["n_claims"] == 2 and s["n_distinct_gaps"] >= 3
    assert any("contradiccion" in g for g in land.gaps())


def test_portfolio_diversifies_across_families():
    vs = scan_vulnerabilities(_claim("c1"))
    ranked = generate_portfolio(vs, _claim("c1"))
    port = build_portfolio(ranked, max_per_family=1, size=8)
    fams = [e.ranked.question.family.value for e in port]
    assert len(fams) == len(set(fams))       # no family repeated (max_per_family=1)
    assert len(family_coverage(port)) >= 2


def test_portfolio_keeps_genealogy_and_only_passed():
    vs = scan_vulnerabilities(_claim("c1"))
    ranked = generate_portfolio(vs, _claim("c1"))
    port = build_portfolio(ranked)
    for e in port:
        assert e.ranked.verdict.passed
        assert e.lineage["target_vulnerability"] and e.lineage["origin"]
