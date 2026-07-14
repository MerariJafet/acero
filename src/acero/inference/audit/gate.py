"""Mandatory epistemic gate (Sprint 8.9).

A candidate cannot reach HUMAN_REVIEW if it fails any critical deterministic check.
Codex is an ADVISORY auditor: a Codex finding becomes a blocker only when it maps to
an existing rule (or a human promotes it to a rule). No conclusion passes if it
overstates the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..models import IdentifiabilityStatus


class GateStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    BLOCKED = "BLOCKED"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


@dataclass
class GateFinding:
    rule: str
    severity: str      # blocker | warning
    detail: str


# Every deterministic blocker rule id (used to promote Codex findings).
BLOCKER_RULES = {
    "invalid_dimensions", "missing_provenance", "data_leakage", "no_baseline",
    "no_controls", "not_reproducible", "harking", "negative_result_deleted",
    "non_identifiable_presented_as_unique", "undeclared_miscalibration",
    "extrapolation_without_test", "causal_claim_without_evidence",
    "equivalent_counted_as_new", "codex_as_evidence",
}


@dataclass
class GateInput:
    dimensions_valid: bool = True
    has_provenance: bool = True
    train_test_disjoint: bool = True
    has_baseline: bool = True
    has_controls: bool = True
    reproduced: bool = True
    preregistered: bool = True                 # predictions fixed before results
    negatives_preserved: bool = True
    identifiability: IdentifiabilityStatus = IdentifiabilityStatus.IDENTIFIABLE
    presented_as_unique: bool = False
    calibration_declared: bool = True
    known_miscalibrated: bool = False
    extrapolation_tested: bool = True
    makes_causal_claim: bool = False
    has_intervention_evidence: bool = False
    n_equivalent_models: int = 0
    counts_equivalent_as_new: bool = False
    codex_treated_as_evidence: bool = False
    inference_level: str = "system_identification"


@dataclass
class GateReport:
    status: GateStatus
    findings: list[GateFinding] = field(default_factory=list)

    @property
    def blockers(self) -> list[GateFinding]:
        return [f for f in self.findings if f.severity == "blocker"]

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "n_blockers": len(self.blockers),
                "findings": [f.__dict__ for f in self.findings]}


def evaluate(gi: GateInput, *, codex_findings: list[dict[str, Any]] | None = None
             ) -> GateReport:
    f: list[GateFinding] = []

    def block(rule: str, detail: str) -> None:
        f.append(GateFinding(rule, "blocker", detail))

    def warn(rule: str, detail: str) -> None:
        f.append(GateFinding(rule, "warning", detail))

    if not gi.dimensions_valid:
        block("invalid_dimensions", "the candidate is dimensionally inconsistent")
    if not gi.has_provenance:
        block("missing_provenance", "no provenance recorded")
    if not gi.train_test_disjoint:
        block("data_leakage", "train/test not disjoint")
    if not gi.has_baseline:
        block("no_baseline", "no baseline reported")
    if not gi.has_controls:
        block("no_controls", "no controls reported")
    if not gi.reproduced:
        block("not_reproducible", "result did not reproduce")
    if not gi.preregistered:
        block("harking", "predictions/metrics not fixed before results (HARKing)")
    if not gi.negatives_preserved:
        block("negative_result_deleted", "a negative result was deleted")
    if (gi.identifiability in (IdentifiabilityStatus.NON_IDENTIFIABLE,
                               IdentifiabilityStatus.PARTIALLY_IDENTIFIABLE)
            and gi.presented_as_unique):
        block("non_identifiable_presented_as_unique",
              f"model is {gi.identifiability.value} but presented as the unique answer")
    if gi.known_miscalibrated and not gi.calibration_declared:
        block("undeclared_miscalibration", "known miscalibration not declared")
    if not gi.extrapolation_tested:
        block("extrapolation_without_test", "extrapolation claimed without a test")
    if gi.makes_causal_claim and not gi.has_intervention_evidence:
        block("causal_claim_without_evidence",
              "causal claim without intervention or causal evidence")
    if gi.n_equivalent_models > 1 and gi.counts_equivalent_as_new:
        block("equivalent_counted_as_new",
              f"{gi.n_equivalent_models} equivalent models counted as distinct discoveries")
    if gi.codex_treated_as_evidence:
        block("codex_as_evidence", "Codex output treated as scientific evidence")

    # 'law'/'discovery' framing at a fitting-only level is a warning to escalate.
    if gi.inference_level in ("curve_fitting", "system_identification"):
        warn("level_overstatement_risk",
             f"level is '{gi.inference_level}'; do not call the result a law or mechanism")

    # Codex advisory findings: promote to blocker only if they name a known rule.
    for cf in (codex_findings or []):
        rule = cf.get("rule", "")
        if rule in BLOCKER_RULES:
            block(rule, f"[codex-promoted] {cf.get('detail', '')}")
        else:
            warn(f"codex:{cf.get('concern', 'finding')}", cf.get("detail", ""))

    if any(x.severity == "blocker" for x in f):
        status = GateStatus.BLOCKED
    elif gi.identifiability == IdentifiabilityStatus.DATA_INSUFFICIENT:
        status = GateStatus.ESCALATE_TO_HUMAN
    elif any(x.severity == "warning" for x in f):
        status = GateStatus.PASS_WITH_WARNINGS
    else:
        status = GateStatus.PASS
    return GateReport(status=status, findings=f)
