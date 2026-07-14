"""Adversarial audit of the inference engine (rules + Codex).

Detects: false recovery, privileged library, contaminated derivatives, leakage,
equivalent terms, ignored units, latent variables, poor identifiability,
overconfidence, fit-disguised-as-explanation, circular experiments, and conclusions
stronger than the evidence. Rules are deterministic; Codex is advisory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


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


def rules_audit(inference_report: dict[str, Any]) -> AuditReport:
    f: list[Finding] = []
    lib = inference_report.get("library", {})
    families = set(lib.get("families", []))

    # Privileged library: only polynomial families -> non-polynomial dynamics missed.
    if families and families.issubset({"poly", "interaction"}):
        f.append(Finding("privileged_library",
                         "library is polynomial-only; non-polynomial dynamics cannot be found",
                         "medium"))

    # Contaminated derivatives: many unreliable indices reported.
    for tgt, e in inference_report.get("equations", {}).items():
        if len(e.get("unreliable_index", [])) > 4:
            f.append(Finding("contaminated_derivatives",
                             f"{tgt}: many unreliable derivative regions", "medium"))
        # Overconfidence: high R2 but poor identifiability presented without caveat.
        if e.get("r2", 0) > 0.99 and e.get("identifiability") in (
                "PARTIALLY_IDENTIFIABLE", "NON_IDENTIFIABLE"):
            f.append(Finding("fit_without_identifiability",
                             f"{tgt}: R²>0.99 but {e['identifiability']} — good fit ≠ identified",
                             "high"))

    # Level honesty: claims discovery/law at a fitting-only level.
    level = inference_report.get("inference_level", "")
    if level in ("curve_fitting", "system_identification") and not inference_report.get("honesty"):
        f.append(Finding("overstated_level",
                         "no honesty statement distinguishing fitting from discovery", "high"))

    # Imposed vs inferred must be disclosed.
    if not inference_report.get("imposed"):
        f.append(Finding("imposed_not_disclosed",
                         "does not disclose what was imposed (library/constraints)", "high"))
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

_PROMPT = """You are auditing a governing-structure inference result. Find weaknesses: false
recovery, a privileged term library, contaminated derivatives, data leakage,
algebraically-equivalent terms, ignored units, an unobserved (latent) variable, poor
identifiability, overconfidence, curve-fitting disguised as explanation, a circular
experiment, or a conclusion stronger than the evidence. Return JSON only (findings:
concern, detail, severity).

Inference summary:
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
