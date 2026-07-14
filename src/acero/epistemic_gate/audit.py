"""Adversarial audit of the Global Epistemic Gate itself.

Rule findings are deterministic; Codex findings are advisory. Detects gaps in the gate's
own coverage: stages with no rules, blocker rules that cannot be evaluated for lack of a
declared input, duplicate rule ids across stages, and Codex 'rules' that were promoted
without a checker (which the registry already forbids, so this is a belt-and-braces check).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .engine import PIPELINE
from .models import Severity
from .registry import GateRegistry


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


def rules_audit(registry: GateRegistry | None = None) -> AuditReport:
    reg = registry or GateRegistry()
    f: list[Finding] = []

    seen_ids: dict[str, str] = {}
    for stage in PIPELINE:
        rules = reg.rules_for(stage)
        # QUESTION stage intentionally has no dedicated rules (governed via hypothesis).
        if not rules and stage.value not in ("QUESTION",):
            f.append(Finding("stage_without_rules",
                             f"stage {stage.value} has no rules", "medium"))
        for r in rules:
            if r.id in seen_ids and seen_ids[r.id] != stage.value:
                f.append(Finding("duplicate_rule_id",
                                 f"rule id '{r.id}' appears in {seen_ids[r.id]} and "
                                 f"{stage.value}", "high"))
            seen_ids[r.id] = stage.value
            if r.severity == Severity.BLOCKER and not r.inputs and r.source != "codex-promoted":
                # a blocker with no declared inputs can't announce what it needs
                f.append(Finding("blocker_without_declared_inputs",
                                 f"blocker '{r.id}' declares no inputs", "low"))
            if r.source == "codex-promoted" and not callable(r.checker):
                f.append(Finding("codex_rule_without_checker",
                                 f"promoted rule '{r.id}' has no checker", "high"))
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

_PROMPT = """You are auditing a transversal Epistemic Gate that governs a scientific
pipeline (literature → publication). Find coverage gaps or ways it could be bypassed:
stages with weak/missing rules, blockers that never trigger, rules that contradict each
other, or an over-strict gate that would block legitimate low-risk work. Codex output is
advisory only; a finding becomes a rule only with a verifiable checker and test. Return
JSON only (findings: concern, detail, severity).

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
