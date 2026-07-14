"""Adversarial audit of a discovery run (rules + optional Codex).

A deterministic rule-based auditor checks the report for the classic failure modes
(confirmation bias, privileged hypotheses, leakage, false novelty, miscalibration,
post-hoc selection, non-discriminating experiments, hidden costs, fragility,
overclaims). An optional Codex auditor adds advisory findings. Codex output is never
treated as authoritative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    concern: str
    detail: str
    severity: str  # high | medium | low | info
    source: str = "rules"


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"n_findings": len(self.findings),
                "findings": [f.__dict__ for f in self.findings]}


def rules_audit(report: dict[str, Any]) -> AuditReport:
    f: list[Finding] = []

    # Privileged hypothesis: the winning family is among the offered candidates AND
    # the data were generated from it. Honest only if explicitly disclosed.
    if report.get("winner_family") == report.get("hidden_family"):
        disclosed = any("privilegiad" in s for s in report.get("cannot_conclude", []))
        f.append(Finding(
            "privileged_hypothesis",
            "Winner equals the hidden generating family; this is model recovery. "
            + ("Disclosed in cannot_conclude." if disclosed else "NOT disclosed."),
            "info" if disclosed else "high"))

    # Data leakage.
    metrics = report.get("family_mean_test_rmse", {})
    if not report.get("diversity"):
        f.append(Finding("missing_diversity", "No diversity report present.", "medium"))

    # Miscalibration: overconfident posterior.
    post = report.get("confidence_posterior", {})
    if post and max(post.values(), default=0) >= 0.99:
        f.append(Finding("overconfidence",
                         f"Posterior places >=0.99 on one hypothesis: {post}.", "high"))

    # Non-discriminating experiment.
    if report.get("eig_bits", 0) <= 0:
        f.append(Finding("non_discriminating",
                         "EIG is zero; the experiment may not distinguish hypotheses.", "high"))

    # False novelty / overclaim.
    if not report.get("honesty"):
        f.append(Finding("overclaim", "No honesty statement in the report.", "high"))
    if not report.get("cannot_conclude"):
        f.append(Finding("overclaim", "No 'cannot_conclude' limitations.", "high"))

    # Hidden costs.
    f.append(Finding("hidden_costs",
                     "Local-first: no paid services used; sandboxed execution only.", "info"))

    # Fragility: sensitivity to priors.
    sens = report.get("prior_sensitivity", {})
    if sens.get("range", 0) > 0.5:
        f.append(Finding("prior_fragility",
                         f"EIG varies a lot with the prior (range={sens.get('range')}).", "medium"))

    # Post-hoc selection: metric fixed before results (preregistration).
    if metrics and report.get("winner_family") not in metrics:
        f.append(Finding("post_hoc",
                         "Winner family not in reported metric table; check selection.", "medium"))

    return AuditReport(findings=f)


AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "concern": {"type": "string"},
                    "detail": {"type": "string"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["concern", "detail", "severity"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

_PROMPT = """You are an adversarial scientific auditor. Review this discovery-benchmark
report and find weaknesses: confirmation bias, privileged hypotheses, data leakage,
false novelty, miscalibration, post-hoc metric selection, non-discriminating
experiments, hidden costs, fragility, and overclaims. Be specific and skeptical.
Return JSON only (findings: concern, detail, severity high|medium|low).

Report:
{report}"""


def codex_audit(report: dict[str, Any], provider: Any) -> AuditReport:
    if not hasattr(provider, "complete_json"):
        return AuditReport(findings=[])
    prompt = _PROMPT.format(report=json.dumps(report, ensure_ascii=False, default=str)[:6000])
    try:
        result = provider.complete_json(prompt, AUDIT_SCHEMA)
    except Exception as exc:  # noqa: BLE001 - advisory
        return AuditReport(findings=[Finding("audit_error", str(exc), "low", source="codex")])
    return AuditReport(findings=[
        Finding(i.get("concern", "?"), i.get("detail", ""), i.get("severity", "low"), source="codex")
        for i in result.get("findings", [])
    ])
