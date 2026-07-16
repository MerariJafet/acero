"""Improvement proposals (Sprint 18).

ACERO may PROPOSE an improvement; it never applies a high-impact change automatically. Every
proposal must carry evidence, expected benefit/cost, scientific + technical risk, required
tests, and a rollback plan. A proposal without evidence is refused.
"""

from __future__ import annotations

from ..discovery.store import DiscoveryStore
from .models import ImprovementProposal, ProposalStatus

PROPOSAL_SCOPE = "_proposals"


class ProposalError(RuntimeError):
    """Raised when a proposal is malformed (no evidence, no rollback for high impact)."""


class ProposalRegistry:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    def propose(self, proposal: ImprovementProposal) -> ImprovementProposal:
        if not proposal.evidence:
            raise ProposalError("an improvement proposal requires evidence")
        if not proposal.rollback_plan:
            raise ProposalError("an improvement proposal requires a rollback plan")
        self._store.put(PROPOSAL_SCOPE, "proposal", proposal.proposal_id,
                        proposal.model_dump(), status=proposal.status.value,
                        summary=f"proposal: {proposal.problem[:50]}")
        return proposal

    def decide(self, proposal_id: str, status: ProposalStatus, *, human_decision: str
               ) -> ImprovementProposal:
        """Only a human moves a proposal beyond PROPOSED; recorded with the decision."""
        raw = self._store.get(proposal_id)
        if raw is None:
            raise KeyError(proposal_id)
        p = ImprovementProposal(**raw)
        p.status = status
        p.human_decision = human_decision
        self._store.put(PROPOSAL_SCOPE, "proposal", p.proposal_id, p.model_dump(),
                        status=status.value, summary=f"proposal -> {status.value}")
        return p

    def all(self) -> list[ImprovementProposal]:
        return [ImprovementProposal(**r)
                for r in self._store.list_objects(PROPOSAL_SCOPE, kind="proposal")]
