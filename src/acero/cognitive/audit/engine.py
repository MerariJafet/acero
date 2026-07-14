"""Adversarial audit of the Cognitive Discovery Engine (rules + Codex).

Rule findings are deterministic; Codex findings are advisory. Detects: surface-only
analogies, invented relations, circularity, false equivalence, lost units, incomplete
derivations, hidden terms, undeclared assumptions, conceptual overfitting, and
language that sounds deeper than it is.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ...world_model.graph import WorldModel
from ..analogies.engine import AnalogyEngine
from ..analogies.models import AnalogyStatus
from ..concepts.engine import ConceptEngine
from ..first_principles.models import ScientificDerivation


@dataclass
class Finding:
    concern: str
    detail: str
    severity: str
    source: str = "rules"


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"n_findings": len(self.findings),
                "findings": [f.__dict__ for f in self.findings]}


def rules_audit(wm: WorldModel, *, derivations: list[ScientificDerivation] | None = None
                ) -> AuditReport:
    f: list[Finding] = []
    ae = AnalogyEngine(wm)
    ce = ConceptEngine(wm)

    # Surface-only analogies must be flagged MISLEADING, not accepted as deep.
    for a in ae.analogies():
        deep = a.status in {AnalogyStatus.STRUCTURALLY_SUPPORTED, AnalogyStatus.VALID_IN_REGIME}
        if deep and a.scores.structural_similarity < 0.5:
            f.append(Finding("shallow_analogy_marked_deep",
                             f"'{a.source_system}~{a.target_system}' is {a.status.value} "
                             f"but structural_similarity={a.scores.structural_similarity}",
                             "high"))
        if a.status == AnalogyStatus.MISLEADING and not a.failure_conditions:
            f.append(Finding("misleading_without_explanation",
                             "misleading analogy has no failure_conditions", "medium"))

    # Concepts asserted by Codex but never verified.
    unverified = ce.unverified_concepts()
    if unverified:
        f.append(Finding("unverified_codex_concepts",
                         f"{len(unverified)} concept(s) from Codex not verified: "
                         f"{unverified[:5]}", "medium"))

    # Derivations presented as complete but with unresolved steps or confidence≥1.
    for d in (derivations or []):
        if d.confidence >= 1.0:
            f.append(Finding("derivation_overconfident",
                             f"derivation '{d.target}' claims confidence>=1.0", "high"))
        if d.conclusion and d.unresolved_steps:
            f.append(Finding("incomplete_derivation_presented_as_done",
                             f"'{d.target}' has a conclusion but unresolved steps "
                             f"{d.unresolved_steps}", "high"))
    return AuditReport(f)


AUDIT_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"concern": {"type": "string"}, "detail": {"type": "string"},
                       "severity": {"type": "string", "enum": ["high", "medium", "low"]}},
        "required": ["concern", "detail", "severity"], "additionalProperties": False}}},
    "required": ["findings"], "additionalProperties": False,
}

_PROMPT = """You are auditing a computational Cognitive Discovery Engine (concepts, analogies,
derivations). Find weaknesses: superficial analogies dressed as deep, invented
relations, circular reasoning, false equivalence, lost units, incomplete derivations,
hidden terms, undeclared assumptions, conceptual overfitting, or language that sounds
deeper than the evidence supports, or 'first-principles' claims that are actually
recalled from literature. Return JSON only (findings: concern, detail, severity).

Summary:
{summary}"""


def codex_audit(summary: dict[str, Any], provider: Any) -> AuditReport:
    if not hasattr(provider, "complete_json"):
        return AuditReport()
    prompt = _PROMPT.format(summary=json.dumps(summary, default=str)[:6000])
    try:
        result = provider.complete_json(prompt, AUDIT_SCHEMA)
    except Exception as exc:  # noqa: BLE001
        return AuditReport([Finding("audit_error", str(exc), "low", source="codex")])
    return AuditReport([Finding(i.get("concern", "?"), i.get("detail", ""),
                                i.get("severity", "low"), source="codex")
                        for i in result.get("findings", [])])
