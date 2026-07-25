"""F3 — EVA runner with two modes.

  EXTERNAL_KNOWLEDGE_AUDIT: reconstruct + stress-test an existing theory/consensus.
  INTERNAL_HYPOTHESIS_AUDIT: attack ACERO's OWN freshly generated hypotheses BEFORE
    spending resources — catching reformulations, vagueness, post-hoc origin, simpler
    explanations, confirm-only designs and trivial effects.

Both modes reuse the vulnerability scanner and add mode-specific checks. EVA is never
evidence; its output is a prioritized, actionable vulnerability surface plus (for internal
mode) a go/hold recommendation before committing experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .assumption_auditor import AssumptionAudit, audit_assumptions
from .claim_reconstructor import ClaimRecord
from .vulnerability import EpistemicVulnerability, VulnerabilityType, scan_vulnerabilities


class EvaMode(str, Enum):
    EXTERNAL_KNOWLEDGE_AUDIT = "external_knowledge_audit"
    INTERNAL_HYPOTHESIS_AUDIT = "internal_hypothesis_audit"


@dataclass
class InternalHypothesisFlags:
    """Signals about a freshly generated hypothesis (from lineage/search ledger)."""
    is_reformulation_of_known: bool = False
    too_vague_to_refute: bool = False
    arose_after_seeing_results: bool = False
    simpler_explanation_exists: bool = False
    dataset_cannot_answer: bool = False
    experiment_confirm_only: bool = False
    effect_would_be_trivial: bool = False
    depends_on_single_decision: bool = False


@dataclass
class EvaReport:
    mode: EvaMode
    claim_id: str
    vulnerabilities: list[EpistemicVulnerability]
    assumption_audits: list[AssumptionAudit] = field(default_factory=list)
    internal_blockers: list[str] = field(default_factory=list)

    @property
    def n_actionable(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.actionable)

    @property
    def recommend_proceed(self) -> bool:
        """Internal mode: do NOT spend experiments on a hypothesis with fatal internal
        blockers (reformulation / vague / post-hoc / confirm-only / trivial)."""
        return not self.internal_blockers

    def summary(self) -> dict[str, object]:
        return {
            "mode": self.mode.value, "claim_id": self.claim_id,
            "n_vulnerabilities": len(self.vulnerabilities),
            "n_actionable": self.n_actionable,
            "critical_assumptions": [a.assumption for a in self.assumption_audits
                                     if a.critical],
            "internal_blockers": self.internal_blockers,
            "recommend_proceed": self.recommend_proceed,
            "top_vulnerabilities": [v.type.value for v in self.vulnerabilities[:5]],
        }


def audit_external(claim: ClaimRecord, *, validated: set[str] | None = None,
                   sensitivities: dict[str, float] | None = None) -> EvaReport:
    """Mode A: reconstruct + stress-test existing knowledge."""
    return EvaReport(
        mode=EvaMode.EXTERNAL_KNOWLEDGE_AUDIT, claim_id=claim.claim_id,
        vulnerabilities=scan_vulnerabilities(claim),
        assumption_audits=audit_assumptions(claim, validated, sensitivities))


def audit_internal(hypothesis: ClaimRecord,
                   flags: InternalHypothesisFlags | None = None) -> EvaReport:
    """Mode B: attack ACERO's own hypothesis before spending resources."""
    f = flags or InternalHypothesisFlags()
    blockers: list[str] = []
    if f.is_reformulation_of_known:
        blockers.append("es una reformulación de algo ya conocido")
    if f.too_vague_to_refute:
        blockers.append("demasiado vaga para ser refutada")
    if f.arose_after_seeing_results:
        blockers.append("surgió después de ver el resultado (HARKing)")
    if f.experiment_confirm_only:
        blockers.append("el experimento propuesto solo puede confirmarla")
    if f.effect_would_be_trivial:
        blockers.append("el supuesto descubrimiento sería científicamente trivial")
    if f.dataset_cannot_answer:
        blockers.append("el dataset no puede responder realmente la pregunta")
    # non-fatal warnings become vulnerabilities
    vulns = scan_vulnerabilities(hypothesis)
    if f.simpler_explanation_exists:
        vulns.insert(0, EpistemicVulnerability(
            f"{hypothesis.claim_id}.occam", hypothesis.claim_id,
            VulnerabilityType.AMBIGUOUS_MECHANISM,
            "existe una explicación más simple no descartada",
            decisive_test="comparar con el modelo más simple (navaja de Occam)",
            cheapest_probe="ajustar el baseline simple primero",
            severity=0.6, testability=0.7))
    if f.depends_on_single_decision:
        vulns.insert(0, EpistemicVulnerability(
            f"{hypothesis.claim_id}.single", hypothesis.claim_id,
            VulnerabilityType.POSTHOC_SELECTION,
            "el resultado depende de una única decisión metodológica",
            decisive_test="análisis de especificación (multiverse)",
            cheapest_probe="variar 1 decisión y ver estabilidad",
            severity=0.6, testability=0.7))
    vulns.sort(key=lambda x: -x.priority)
    return EvaReport(EvaMode.INTERNAL_HYPOTHESIS_AUDIT, hypothesis.claim_id,
                     vulns, audit_assumptions(hypothesis), blockers)
