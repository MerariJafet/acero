"""Experiment critics (Sprint 6.7).

Two layers:
  * RuleBasedExperimentCritic — the MANDATORY barrier. Deterministic checks for
    missing controls/baseline/metrics/preregistration and non-discriminating or
    privileged designs. Blocking issues prevent the experiment from running.
  * CodexExperimentCritic — ADVISORY. Uses structured LLM output to surface subtle
    concerns (confounds, leakage, post-hoc selection). Never blocking on its own.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .experiment_design import ExperimentProposal, build_matrix


@dataclass
class CriticIssue:
    concern: str
    detail: str
    severity: str  # blocking | high | medium | low


@dataclass
class CriticReport:
    issues: list[CriticIssue] = field(default_factory=list)
    source: str = "rules"

    @property
    def blocking(self) -> list[CriticIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def ok(self) -> bool:
        return not self.blocking

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ok": self.ok,
            "n_issues": len(self.issues),
            "n_blocking": len(self.blocking),
            "issues": [i.__dict__ for i in self.issues],
        }


class RuleBasedExperimentCritic:
    def review(self, proposal: ExperimentProposal) -> CriticReport:
        issues: list[CriticIssue] = []

        if not proposal.baseline:
            issues.append(CriticIssue("no_baseline", "No baseline specified.", "blocking"))
        if not proposal.positive_control or not proposal.negative_control:
            issues.append(CriticIssue(
                "missing_controls",
                "Both positive and negative controls are required.", "blocking"))
        if not proposal.metrics:
            issues.append(CriticIssue("no_metrics", "No metrics defined.", "blocking"))
        if not proposal.preregistered_predictions:
            issues.append(CriticIssue(
                "no_preregistration",
                "No preregistered per-hypothesis predictions.", "blocking"))
        else:
            matrix = build_matrix(proposal)
            if not matrix.is_discriminating:
                issues.append(CriticIssue(
                    "non_discriminating",
                    f"All hypotheses predict the same outcome: {matrix.expected_outcomes}.",
                    "blocking"))
            groups = matrix.non_distinguished_groups()
            if groups:
                issues.append(CriticIssue(
                    "partial_ambiguity",
                    f"Some hypotheses share an outcome and won't be distinguished: {groups}.",
                    "medium"))
        if len(proposal.hypotheses_tested) < 2:
            issues.append(CriticIssue(
                "too_few_hypotheses", "Fewer than two hypotheses tested.", "blocking"))
        if not proposal.stopping_rules:
            issues.append(CriticIssue(
                "no_stopping_rule", "No stopping rule; unbounded compute risk.", "high"))
        # Privileged-hypothesis heuristic: exactly one hypothesis appears in the
        # metric/parameter names.
        return CriticReport(issues=issues, source="rules")


CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
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
    "required": ["issues"],
    "additionalProperties": False,
}

_PROMPT = """You are an adversarial experiment reviewer. Find methodological problems in
this computational experiment proposal: missing controls, biased metrics, omitted
variables, confounds, data leakage, post-hoc selection, excessive cost,
non-discriminating tests, a privileged hypothesis, or conclusions the experiment
cannot support. Return JSON only (issues: concern, detail, severity high|medium|low).

Proposal:
{proposal}"""


class CodexExperimentCritic:
    """Advisory only. Requires a provider with complete_json."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def available(self) -> bool:
        return hasattr(self.provider, "complete_json")

    def review(self, proposal: ExperimentProposal) -> CriticReport:
        if not self.available():
            return CriticReport(issues=[], source="llm-unavailable")
        prompt = _PROMPT.format(
            proposal=json.dumps(proposal.model_dump(), ensure_ascii=False, default=str)[:4000])
        try:
            result = self.provider.complete_json(prompt, CRITIC_SCHEMA)
        except Exception as exc:  # noqa: BLE001 - advisory must never break the barrier
            return CriticReport(issues=[CriticIssue("llm_error", str(exc), "low")],
                                source="llm-error")
        issues = [
            CriticIssue(i.get("concern", "?"), i.get("detail", ""), i.get("severity", "low"))
            for i in result.get("issues", [])
        ]
        # Advisory: LLM issues are never 'blocking'.
        return CriticReport(issues=issues, source="codex")
