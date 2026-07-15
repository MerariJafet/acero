"""Scientific Reliability Engine orchestrator (Sprint 11).

Runs the reliability probes (red team, scientific mutation, domain reliability, gauntlet)
and assembles a ScientificReliabilityCard — reporting each dimension separately, never a
single magic trust score — then computes a readiness level and a (never-auto-publishing)
publication candidate.
"""

from __future__ import annotations

from typing import Any

from .domain_reliability import run_domain_reliability
from .mutation import run_mutation_testing
from .red_team import run_red_team
from .scorecard import (
    PublicationCandidate,
    ReadinessLevel,
    ScientificReliabilityCard,
)


def build_card(subject: str = "acero-pipeline") -> ScientificReliabilityCard:
    """Measure each reliability dimension from the actual probes."""
    rt = run_red_team().as_dict()
    mut = run_mutation_testing().as_dict()
    dom = run_domain_reliability()

    card = ScientificReliabilityCard(subject=subject)
    # adversarial robustness = fraction of attacks detected
    card.set("adversarial_robustness", rt["detected"] / rt["n"], rt["n"],
             limitation="library v1; not exhaustive", trend="up")
    # numerical stability from domain reliability (physics convergence + stiffness)
    stable = all(dom[d]["passed"] for d in ("physics", "chemistry"))
    card.set("numerical_stability", 1.0 if stable else 0.4, 4,
             limitation="synthetic solvers, 1-D", trend="flat")
    # domain validity = fraction of domain reliability checks passing
    dom_pass = sum(1 for r in dom.values() if r["passed"]) / len(dom)
    card.set("domain_validity", dom_pass, len(dom), limitation="computational only")
    # gate compliance from scientific mutation coverage
    card.set("gate_compliance", mut["caught"] / mut["n"], mut["n"],
             limitation="mutation set v1")
    # the remaining dimensions are context-supplied; default to insufficient (None)
    for name in ("reproducibility", "calibration", "evidence_independence",
                 "human_understanding", "provenance_completeness",
                 "unresolved_contradictions", "abstention_quality"):
        card.set(name, None, 0, limitation="not measured for this subject")
    return card


def run_reliability(subject: str = "acero-pipeline", *,
                    reproducibility: float | None = None,
                    calibration: float | None = None,
                    evidence_independence: float | None = None,
                    human_understanding: float | None = None,
                    provenance: float | None = None,
                    abstention_quality: float | None = None,
                    unresolved_contradictions: int = 0,
                    gate_complete: bool = True,
                    externally_validated: bool = False) -> dict[str, Any]:
    """Assemble a full reliability assessment for a subject."""
    card = build_card(subject)
    # fill context-supplied dimensions when provided
    supplied = {"reproducibility": reproducibility, "calibration": calibration,
                "evidence_independence": evidence_independence,
                "human_understanding": human_understanding,
                "provenance_completeness": provenance,
                "abstention_quality": abstention_quality}
    for name, val in supplied.items():
        if val is not None:
            card.set(name, val, 1)
    card.set("unresolved_contradictions",
             1.0 if unresolved_contradictions == 0 else 0.0, 1)

    pc = PublicationCandidate(project=subject, central_claim="(subject under assessment)",
                              reliability_card=card)
    pc.evaluate(gate_complete=gate_complete,
                human_understands=bool(human_understanding and human_understanding >= 0.7),
                externally_validated=externally_validated,
                unresolved_contradictions=unresolved_contradictions)
    return {"card": card.as_dict(), "readiness": pc.readiness.value,
            "blockers": pc.blockers, "publication_candidate": pc.as_dict(),
            "note": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW is the ceiling; "
                    "DISCOVERY_CONFIRMED does not exist and is never granted."}


def readiness_levels() -> list[str]:
    return [lvl.value for lvl in ReadinessLevel]
