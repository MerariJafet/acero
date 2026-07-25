"""F8 — Epistemic pipeline: topic → knowledge map → vulnerabilities → questions → rivals
→ discriminating test → READY_FOR_EXPLORATORY_RESEARCH.

This is the integrated flow the reviewer asked for. It threads the epistemic engines
together and drives the pre-research state machine so that a general topic can NEVER jump
straight to a confirmatory experiment — it must first become a discriminating test. It
records the semantic exploration (anti-HARKing) and hands off to the Constitution's
exploratory regime.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..questions.knowledge_landscape import KnowledgeLandscape
from ..questions.portfolio import PortfolioEntry, build_portfolio
from ..questions.question_engine import generate_portfolio
from ..science.discrimination import DiscriminatingTest, design_discriminating_test
from ..science.lineage import SemanticExplorationLedger
from ..science.pre_research_states import (
    PreResearchEvidence,
    PreResearchState,
    max_reachable,
    next_required,
)
from .claim_reconstructor import ClaimRecord
from .rival_theory_generator import generate_rivals
from .vulnerability import scan_vulnerabilities


@dataclass
class PipelineResult:
    topic: str
    n_claims: int
    n_vulnerabilities: int
    portfolio: list[PortfolioEntry]
    top_question_id: str
    discriminating_test: DiscriminatingTest | None
    state: PreResearchState
    next_required: str
    semantic: SemanticExplorationLedger

    @property
    def ready_for_exploratory(self) -> bool:
        return self.state is PreResearchState.READY_FOR_EXPLORATORY_RESEARCH

    def summary(self) -> dict[str, object]:
        return {
            "topic": self.topic, "n_claims": self.n_claims,
            "n_vulnerabilities": self.n_vulnerabilities,
            "n_questions": len(self.portfolio),
            "top_question": self.top_question_id,
            "discriminating_test_bits":
                round(self.discriminating_test.expected_information_gain(), 3)
                if self.discriminating_test else None,
            "state": self.state.name,
            "next_required": self.next_required,
            "ready_for_exploratory": self.ready_for_exploratory,
            "semantic": self.semantic.summary(),
        }


def run_pipeline(topic: str, claims: list[ClaimRecord],
                 confounder_candidates: tuple[str, ...] = ()) -> PipelineResult:
    """Run the full topic→discriminating-test pipeline."""
    sem = SemanticExplorationLedger()
    ev = PreResearchEvidence()

    # 1) knowledge landscape (claims already reconstructed upstream)
    land = KnowledgeLandscape(topic)
    for c in claims:
        land.add_claim(c)
    ev.knowledge_mapped = bool(claims)
    ev.claims_reconstructed = bool(claims)

    # 2) vulnerability surface across the topic
    surface = land.vulnerability_surface()
    ev.vulnerabilities_identified = bool(surface)

    # 3) questions (targeted at vulnerabilities) + diversified, gated portfolio
    ranked = []
    for c in claims:
        vs = scan_vulnerabilities(c)
        ranked.extend(generate_portfolio(vs, c))
    for r in ranked:
        sem.question(r.question.question_text[:80])
    portfolio = build_portfolio(ranked)
    ev.questions_generated = bool(ranked)
    ev.questions_prioritized = bool(portfolio)

    # 4) rivals + discriminating test for the top question
    test: DiscriminatingTest | None = None
    top_qid = ""
    if portfolio and surface:
        top = portfolio[0]
        top_qid = top.ranked.question.question_id
        target_vuln = next((v for c in claims for v in scan_vulnerabilities(c)
                            if v.vulnerability_id == top.ranked.question.target_vulnerability),
                           surface[0])
        target_claim = next((c for c in claims
                             if c.claim_id == target_vuln.target_claim), claims[0])
        rivals = generate_rivals(target_vuln, target_claim, confounder_candidates,
                                 question_id=top_qid)
        ev.rival_hypotheses_defined = rivals.is_well_posed()
        test = design_discriminating_test(rivals, independence_possible=True)
        ev.discriminating_test_designed = test.decisive

    return PipelineResult(
        topic=topic, n_claims=len(claims), n_vulnerabilities=len(surface),
        portfolio=portfolio, top_question_id=top_qid, discriminating_test=test,
        state=max_reachable(ev), next_required=next_required(ev), semantic=sem)
