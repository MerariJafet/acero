"""Belief state and its (configurable) update rules.

Every node in the World Model is a BELIEF with a level of support — never an
absolute truth. Confidence is DERIVED from evidence, counter-evidence, replication,
negatives, and contradictions by a configurable policy (no universal formula).
History is versioned; nothing is overwritten silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.clock import now_iso


@dataclass
class BeliefPolicy:
    """Configurable weights for deriving confidence. Not a scientific truth."""

    replication_bonus: float = 0.08      # per independent replication
    replication_cap: float = 0.3
    contradiction_penalty: float = 0.15  # per open contradiction
    negative_penalty: float = 0.05       # per preserved negative result
    single_source_penalty: float = 0.1   # if support rests on a single source
    prior: float = 0.2                   # confidence with no evidence at all
    smoothing: float = 1.0               # pseudo-count: prevents 1.0 from one datum
    max_confidence: float = 0.98         # never certain; no absolute truths


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


class BeliefState:
    """Mutable support record for a node. Serialisable; keeps full history."""

    def __init__(
        self,
        confidence: float = 0.2,
        evidence_strength: float = 0.0,
        counter_strength: float = 0.0,
        replication_count: int = 0,
        negative_results: int = 0,
        contradictions: int = 0,
        open_questions: int = 0,
        distinct_sources: int = 0,
        last_update: str | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> None:
        self.confidence = confidence
        self.evidence_strength = evidence_strength
        self.counter_strength = counter_strength
        self.replication_count = replication_count
        self.negative_results = negative_results
        self.contradictions = contradictions
        self.open_questions = open_questions
        self.distinct_sources = distinct_sources
        self.last_update = last_update or now_iso()
        self.history: list[dict[str, Any]] = history or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": round(self.confidence, 4),
            "evidence_strength": round(self.evidence_strength, 4),
            "counter_strength": round(self.counter_strength, 4),
            "replication_count": self.replication_count,
            "negative_results": self.negative_results,
            "contradictions": self.contradictions,
            "open_questions": self.open_questions,
            "distinct_sources": self.distinct_sources,
            "last_update": self.last_update,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BeliefState:
        d = dict(d)
        return cls(**{k: d[k] for k in (
            "confidence", "evidence_strength", "counter_strength", "replication_count",
            "negative_results", "contradictions", "open_questions", "distinct_sources",
            "last_update", "history") if k in d})

    def derive_confidence(self, policy: BeliefPolicy) -> float:
        """Recompute confidence from the support record using the policy.

        Smoothed base: (evidence + prior·k) / (evidence + counter + k). One datum
        cannot drive confidence to 1.0 — it saturates gradually with more evidence,
        replication, and distinct sources. Confidence is capped below 1.0 (no
        absolute truths).
        """
        total = self.evidence_strength + self.counter_strength
        if total <= 0:
            base = policy.prior
        else:
            k = policy.smoothing
            base = (self.evidence_strength + policy.prior * k) / (total + k)
        rep = min(policy.replication_cap, policy.replication_bonus * self.replication_count)
        pen = (policy.contradiction_penalty * self.contradictions
               + policy.negative_penalty * self.negative_results)
        if self.distinct_sources <= 1 and self.evidence_strength > 0:
            pen += policy.single_source_penalty
        return min(policy.max_confidence, _clip(base + rep - pen))

    def apply(self, *, event: str, evidence: float = 0.0, counter: float = 0.0,
              replication: int = 0, negative: int = 0, contradiction: int = 0,
              open_question: int = 0, source: str | None = None,
              policy: BeliefPolicy | None = None) -> dict[str, Any]:
        """Apply an update, recompute confidence, and append a history entry.

        Returns the history entry. Nothing is overwritten; the previous confidence
        is retained in history so the belief's trajectory is reconstructable.
        """
        policy = policy or BeliefPolicy()
        before = self.confidence
        self.evidence_strength += evidence
        self.counter_strength += counter
        self.replication_count += replication
        self.negative_results += negative
        self.contradictions += contradiction
        self.open_questions += open_question
        if source:
            # distinct_sources is tracked coarsely via the history of source ids.
            seen = {h.get("source") for h in self.history if h.get("source")}
            if source not in seen:
                self.distinct_sources += 1
        self.confidence = self.derive_confidence(policy)
        self.last_update = now_iso()
        entry = {
            "event": event, "at": self.last_update, "source": source,
            "confidence_before": round(before, 4), "confidence_after": round(self.confidence, 4),
            "delta": round(self.confidence - before, 4),
            "evidence": evidence, "counter": counter, "replication": replication,
            "negative": negative, "contradiction": contradiction,
        }
        self.history.append(entry)
        return entry
