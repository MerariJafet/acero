"""EP3: scientific question engine — questions linked to vulnerabilities, gated (offline)."""

from __future__ import annotations

from acero.epistemic.claim_reconstructor import ClaimRecord, EvidenceType, ReplicationStatus
from acero.epistemic.vulnerability import scan_vulnerabilities
from acero.questions.question_engine import (
    QuestionFamily,
    ScientificQuestion,
    ScientificQuestionCard,
    generate_portfolio,
    quality_gate,
)


def _claim():
    return ClaimRecord(
        claim_id="c1", claim_text="polaridad→permeabilidad",
        exposure_or_input="polaridad", outcome_or_prediction="permeabilidad",
        effect_direction="negativa", evidence_type=EvidenceType.OBSERVATIONAL,
        provenance_roots=("TDC",), replication_status=ReplicationStatus.INTERNAL_ONLY)


def test_every_question_is_linked_to_a_vulnerability():
    vs = scan_vulnerabilities(_claim())
    portfolio = generate_portfolio(vs, _claim())
    assert portfolio
    for r in portfolio:
        assert r.question.target_vulnerability
        assert r.question.origin.startswith("vulnerability:")


def test_card_components_are_shown_not_a_single_number():
    card = ScientificQuestionCard(importance=0.8, discriminating_power=0.7)
    rep = card.report()
    assert "components" in rep and len(rep["components"]) >= 12
    assert "priority" in rep


def test_quality_gate_blocks_unfalsifiable_question():
    q = ScientificQuestion("q", "¿?", QuestionFamily.MECHANISM, "human", "v")
    bad = ScientificQuestionCard(falsifiability=0.1)
    v = quality_gate(q, bad)
    assert not v.passed and any("falsable" in r for r in v.reasons)


def test_quality_gate_blocks_novel_but_trivial():
    q = ScientificQuestion("q", "¿?", QuestionFamily.BOUNDARY, "human", "v")
    trivial = ScientificQuestionCard(scientific_novelty=0.9, importance=0.05,
                                     falsifiability=0.8, clarity=0.8)
    v = quality_gate(q, trivial)
    assert not v.passed and any("trivial" in r for r in v.reasons)


def test_transportability_question_from_single_source_vuln():
    vs = scan_vulnerabilities(_claim())
    portfolio = generate_portfolio(vs, _claim())
    fams = {r.question.family for r in portfolio}
    assert QuestionFamily.TRANSPORTABILITY in fams   # single-source/not-replicated → transport


def test_portfolio_sorted_by_priority_passed_first():
    portfolio = generate_portfolio(scan_vulnerabilities(_claim()), _claim())
    prios = [r.priority for r in portfolio]
    assert prios == sorted(prios, reverse=True)
    assert any(r.verdict.passed for r in portfolio)
