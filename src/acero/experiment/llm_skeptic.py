"""LLM-assisted skeptic (Sprint 5 seed).

AUGMENTS the deterministic, rule-based Skeptic — it does not replace it. The
rule-based Skeptic remains authoritative because its checks are verifiable against
the run record. The LLM skeptic proposes *additional* methodological concerns for a
human to consider. Its output is explicitly advisory and is NEVER evidence.

Works with any provider exposing ``complete_json`` (e.g. CodexCliProvider). With a
provider that lacks it (e.g. the mock), it returns a clearly-marked empty result.
"""

from __future__ import annotations

import json
from typing import Any

OBJECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "objections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "concern": {"type": "string"},
                    "question": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["concern", "question", "severity"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["objections"],
    "additionalProperties": False,
}

_PROMPT = """You are an adversarial scientific reviewer. Your job is to try to REFUTE,
not to approve. Given the preregistration and metrics of a computational experiment,
list concrete methodological weaknesses or alternative explanations a careful
reviewer would raise (data leakage, overfitting, metric gaming, limited range,
confounds, fit-vs-explanation, reproducibility gaps). Be specific and skeptical.

Preregistration:
{prereg}

Metrics:
{metrics}

Return JSON only, matching the required schema (objections: concern, question,
severity in {{low, medium, high}})."""


class LLMSkeptic:
    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def available(self) -> bool:
        return hasattr(self.provider, "complete_json")

    def review(self, prereg: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        base: dict[str, Any] = {
            "available": self.available(),
            "advisory": True,
            "is_evidence": False,
            "provider": getattr(self.provider, "name", "unknown"),
            "objections": [],
        }
        if not self.available():
            base["note"] = "Provider does not support structured output; LLM skeptic skipped."
            return base
        prompt = _PROMPT.format(
            prereg=json.dumps(prereg, ensure_ascii=False, default=str)[:4000],
            metrics=json.dumps(metrics, ensure_ascii=False, default=str)[:2000],
        )
        result = self.provider.complete_json(prompt, OBJECTION_SCHEMA)
        base["objections"] = result.get("objections", [])
        return base
