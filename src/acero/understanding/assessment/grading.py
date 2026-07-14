"""Rubric-based grading of open-ended responses.

Grading is by *expected reasoning elements*, not multiple choice, and awards partial
credit. It is deterministic (keyword/element coverage with negation awareness) so a
"grader that always passes" is impossible to hide. Codex may propose a rubric or a
second opinion, but a Codex 'looks good' is NOT a grade — its advisory score is recorded
separately and never overrides the deterministic rubric.

Crucially, grading returns a SCORE only; it never sets mastery. The knowledge-state
machine (which requires multiple distinct evidence kinds) decides status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import EvidenceType, UnderstandingEvidence

_NEGATORS = ("not", "no ", "n't", "never", "without", "isn't", "does not", "cannot")


@dataclass
class GradeResult:
    score: float                       # 0..1 partial credit
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    codex_advisory: float | None = None
    rubric_version: str = "v1"

    def as_dict(self) -> dict[str, object]:
        return {"score": self.score, "matched": self.matched, "missing": self.missing,
                "red_flags": self.red_flags, "codex_advisory": self.codex_advisory,
                "rubric_version": self.rubric_version}


def _mentions(text: str, element: str) -> bool:
    """Does the response cover this expected element? Matches any of its keywords."""
    low = text.lower()
    kws = [k for k in re.split(r"[\s/|]+", element.lower()) if len(k) > 2]
    if not kws:
        return element.lower() in low
    hits = sum(1 for k in kws if k in low)
    return hits >= max(1, len(kws) // 2)


_STOPWORDS = {"the", "and", "for", "with", "that", "this", "are", "was", "has", "not",
              "but", "its", "into", "from", "than", "then", "our", "out", "over"}


def _is_keyword_echo(response: str, expected_elements: list[str]) -> bool:
    """A response that merely restates the rubric keywords (with no explanatory content
    of its own) is an echo, not comprehension. Flagged after an adversarial (Codex) audit
    noted a short answer containing exactly the rubric words could pass. We require at
    least one content word BEYOND the keywords and common filler."""
    resp_words = [w for w in re.split(r"\W+", response.lower()) if len(w) > 2]
    key_words = {w for el in expected_elements
                 for w in re.split(r"\W+", el.lower()) if len(w) > 2}
    if not resp_words:
        return True
    extra_content = [w for w in resp_words
                     if w not in key_words and w not in _STOPWORDS]
    return len(extra_content) == 0


def grade(response: str, expected_elements: list[str], *,
          forbidden_elements: list[str] | None = None,
          rubric_version: str = "v1",
          codex_advisory: float | None = None) -> GradeResult:
    """Score coverage of expected elements; penalise forbidden (wrong) claims and keyword
    echoing (answers that merely restate the rubric words without explaining)."""
    if not expected_elements:
        return GradeResult(0.0, rubric_version=rubric_version,
                           red_flags=["no rubric elements provided"])
    matched: list[str] = []
    missing: list[str] = []
    for el in expected_elements:
        (matched if _mentions(response, el) else missing).append(el)
    base = len(matched) / len(expected_elements)

    red: list[str] = []
    for bad in (forbidden_elements or []):
        if _mentions(response, bad):
            red.append(bad)
    penalty = 0.34 * len(red)

    if base > 0 and _is_keyword_echo(response, expected_elements):
        red.append("keyword_echo_without_explanation")
        penalty += 0.4          # an echo cannot score a full pass

    score = max(0.0, round(base - penalty, 4))
    return GradeResult(score, matched, missing, red, codex_advisory, rubric_version)


def build_evidence(learner_id: str, concept_id: str, evidence_type: EvidenceType,
                   task: str, response: str, expected_elements: list[str], *,
                   confidence: float = 0.5, research_context: str | None = None,
                   forbidden_elements: list[str] | None = None,
                   grader: str = "rubric") -> tuple[UnderstandingEvidence, GradeResult]:
    """Grade a response and package it as UnderstandingEvidence."""
    g = grade(response, expected_elements, forbidden_elements=forbidden_elements)
    ev = UnderstandingEvidence(
        learner_id=learner_id, concept_id=concept_id, evidence_type=evidence_type,
        task=task, response=response, expected_elements=expected_elements,
        score=g.score, confidence=confidence, grader=grader,
        rubric_version=g.rubric_version, research_context=research_context)
    return ev, g
