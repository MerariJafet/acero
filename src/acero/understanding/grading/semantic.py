"""Codex semantic advisory layer.

Codex returns a structured SemanticAssessment (never a bare grade) and must cite fragments
of the response. It can flag valid paraphrase, conceptual coherence, missing nuance,
circular reasoning, contradictions, and unsupported claims. Its suggested_score_range is
ADVISORY: aggregation never lets it certify mastery, and it is optional (fallback to the
deterministic layer if unavailable).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticAssessment:
    paraphrase_validity: float = 0.0        # 0..1 is this a valid restatement?
    conceptual_coherence: float = 0.0
    missing_nuance: list[str] = field(default_factory=list)
    circular_reasoning: bool = False
    contradiction: bool = False
    unsupported_claim: bool = False
    transfer_quality: float = 0.0
    suggested_score_range: tuple[float, float] = (0.0, 1.0)
    rationale: str = ""
    cited_fragments: list[str] = field(default_factory=list)
    available: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"paraphrase_validity": self.paraphrase_validity,
                "conceptual_coherence": self.conceptual_coherence,
                "missing_nuance": self.missing_nuance,
                "circular_reasoning": self.circular_reasoning,
                "contradiction": self.contradiction,
                "unsupported_claim": self.unsupported_claim,
                "transfer_quality": self.transfer_quality,
                "suggested_score_range": list(self.suggested_score_range),
                "rationale": self.rationale, "cited_fragments": self.cited_fragments,
                "available": self.available}


SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "paraphrase_validity": {"type": "number"},
        "conceptual_coherence": {"type": "number"},
        "missing_nuance": {"type": "array", "items": {"type": "string"}},
        "circular_reasoning": {"type": "boolean"},
        "contradiction": {"type": "boolean"},
        "unsupported_claim": {"type": "boolean"},
        "transfer_quality": {"type": "number"},
        "suggested_low": {"type": "number"},
        "suggested_high": {"type": "number"},
        "rationale": {"type": "string"},
        "cited_fragments": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["paraphrase_validity", "conceptual_coherence", "missing_nuance",
                 "circular_reasoning", "contradiction", "unsupported_claim",
                 "transfer_quality", "suggested_low", "suggested_high", "rationale",
                 "cited_fragments"],
    "additionalProperties": False,
}

_PROMPT = """You are an ADVISORY semantic assessor for a science-education system. You do
NOT assign a grade or certify mastery. Given a QUESTION, the EXPECTED reasoning elements,
and a learner RESPONSE, assess whether the response is a valid paraphrase, is conceptually
coherent, omits nuance, is circular, contradicts itself, or makes unsupported claims. You
MUST cite short verbatim fragments of the response for each judgement. Return JSON only.

QUESTION: {question}
EXPECTED: {expected}
RESPONSE: {response}"""


def assess(question: str, expected_elements: list[str], response: str, provider: Any
           ) -> SemanticAssessment:
    """Ask Codex for an advisory semantic assessment. Falls back to unavailable."""
    if provider is None or not hasattr(provider, "complete_json"):
        return SemanticAssessment(available=False, rationale="semantic layer unavailable")
    prompt = _PROMPT.format(question=question[:400],
                            expected="; ".join(expected_elements)[:400],
                            response=response[:1500])
    try:
        r = provider.complete_json(prompt, SEMANTIC_SCHEMA)
    except Exception as exc:  # noqa: BLE001
        return SemanticAssessment(available=False, rationale=f"error: {exc}")
    # A cited fragment must actually appear in the response (anti-fabrication).
    cited = [f for f in r.get("cited_fragments", [])
             if isinstance(f, str) and f.strip() and f.strip().lower() in response.lower()]
    return SemanticAssessment(
        paraphrase_validity=float(r.get("paraphrase_validity", 0.0)),
        conceptual_coherence=float(r.get("conceptual_coherence", 0.0)),
        missing_nuance=list(r.get("missing_nuance", [])),
        circular_reasoning=bool(r.get("circular_reasoning", False)),
        contradiction=bool(r.get("contradiction", False)),
        unsupported_claim=bool(r.get("unsupported_claim", False)),
        transfer_quality=float(r.get("transfer_quality", 0.0)),
        suggested_score_range=(float(r.get("suggested_low", 0.0)),
                               float(r.get("suggested_high", 1.0))),
        rationale=str(r.get("rationale", "")), cited_fragments=cited, available=True)
