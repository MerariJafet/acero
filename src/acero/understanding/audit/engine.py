"""Adversarial audit: does the engine measure UNDERSTANDING, or fake it?

Rule findings are deterministic; Codex findings are advisory. Detects: fake comprehension
measurement, mastery from a single answer, self-report used as evidence, trivial
questions, circular grading, over-reliance on the LLM, a paternalistic/over-blocking gate,
unsafe (unrecorded) override, concepts not tied to the research, technically wrong
explanations (limitations missing), an over-long curriculum, and privacy over-collection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..assessment.transfer import TRANSFER_TASKS
from ..learner.knowledge_state import MASTERY_MIN_DISTINCT_EVIDENCE
from ..models import (
    ExplanationArtifact,
    KnowledgeState,
    KnowledgeStatus,
    LearnerProfile,
    ResearchLearningRequirement,
    UnderstandingEvidence,
)


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


def rules_audit(
    *,
    profile: LearnerProfile | None = None,
    states: list[KnowledgeState] | None = None,
    evidence: list[UnderstandingEvidence] | None = None,
    explanations: list[ExplanationArtifact] | None = None,
    requirements: list[ResearchLearningRequirement] | None = None,
) -> AuditReport:
    f: list[Finding] = []
    states = states or []
    evidence = evidence or []
    explanations = explanations or []
    requirements = requirements or []

    # 1. Mastery from too little / single-kind evidence.
    by_concept: dict[str, list[UnderstandingEvidence]] = {}
    for e in evidence:
        by_concept.setdefault(e.concept_id, []).append(e)
    for st in states:
        if st.status == KnowledgeStatus.MASTERED:
            kinds = {e.evidence_type for e in by_concept.get(st.concept_id, [])}
            if len(kinds) < MASTERY_MIN_DISTINCT_EVIDENCE:
                f.append(Finding("mastery_from_thin_evidence",
                                 f"'{st.concept_id}' MASTERED with only {len(kinds)} "
                                 f"evidence kind(s)", "high"))

    # 2. Self-report exceeding demonstrated ability (overconfidence not surfaced).
    for st in states:
        if st.confidence_self_reported - st.confidence_observed > 0.4:
            f.append(Finding("self_report_over_observed",
                             f"'{st.concept_id}': self {st.confidence_self_reported} vs "
                             f"observed {st.confidence_observed}", "medium"))

    # 2b. Status incoherent with demonstrated ability (Codex-audit fix): a high status
    # with near-zero measured ability dimensions means the status was set without evidence.
    _HIGH = {KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD, KnowledgeStatus.TRANSFER_CAPABLE,
             KnowledgeStatus.MASTERED}
    for st in states:
        demonstrated = max(st.conceptual_understanding, st.procedural_ability,
                           st.mathematical_ability, st.transfer_ability)
        if st.status in _HIGH and demonstrated < 0.5:
            f.append(Finding("status_incoherent_with_ability",
                             f"'{st.concept_id}' is {st.status.value} but max demonstrated "
                             f"ability is {demonstrated}", "high"))

    # 3. Explanations missing limitations (technically overclaiming).
    for ex in explanations:
        if not ex.limitations:
            f.append(Finding("explanation_without_limitations",
                             f"'{ex.subject}' [{ex.level.value}] states no limitation",
                             "high"))
        if ex.level.value in ("mathematical", "computational") and not (
                ex.equations or ex.code_references):
            f.append(Finding("technical_explanation_unlinked",
                             f"'{ex.subject}' [{ex.level.value}] cites no equation/code",
                             "medium"))

    # 4. Concepts not tied to the research (no equation/code/assumption anchor).
    for r in requirements:
        if not (r.related_equations or r.related_code or r.related_assumptions):
            f.append(Finding("concept_not_tied_to_research",
                             f"requirement '{r.concept}' has no research anchor", "medium"))

    # 5. Over-long curriculum: too many BLOCKING requirements for one project.
    blocking = [r for r in requirements if r.blocking]
    if len(blocking) > 12:
        f.append(Finding("curriculum_too_long",
                         f"{len(blocking)} blocking requirements — risk of gate paternalism",
                         "low"))

    # 6. Grading circularity: evidence graded by 'codex' as sole grader.
    codex_graded = [e for e in evidence if e.grader == "codex"]
    if codex_graded:
        f.append(Finding("llm_as_sole_grader",
                         f"{len(codex_graded)} evidence item(s) graded solely by codex",
                         "high"))

    # 7. Trivial assessment: expected_elements empty (nothing to demonstrate).
    trivial = [e for e in evidence if not e.expected_elements]
    if trivial:
        f.append(Finding("trivial_assessment",
                         f"{len(trivial)} assessment(s) with no expected elements", "medium"))

    # 8. Privacy: profile carrying obviously sensitive free-text.
    if profile is not None:
        blob = json.dumps(profile.model_dump()).lower()
        for token in ("password", "ssn", "credit", "dob", "address"):
            if token in blob:
                f.append(Finding("privacy_overcollection",
                                 f"profile appears to contain '{token}'", "high"))

    # 9. Transfer coverage sanity (mastery must be transfer-testable).
    concept_names = {r.concept for r in requirements}
    testable = {t.concept for t in TRANSFER_TASKS}
    mastered = {st.concept_id for st in states if st.status == KnowledgeStatus.MASTERED}
    untestable = mastered - testable
    if untestable:
        f.append(Finding("mastery_without_transfer_task",
                         f"MASTERED without a transfer benchmark: {sorted(untestable)}",
                         "low"))
    _ = concept_names  # reserved for future cross-checks

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

_PROMPT = """You are auditing a Human Understanding Engine that tries to keep a human
researcher intellectually inside the scientific loop. Look for ways it might FAKE
understanding rather than measure it: comprehension inferred from self-report or an LLM
answer, mastery granted from a single answer, trivial questions, circular grading (the
grader always passes), over-reliance on the LLM, a paternalistic gate that blocks
low-risk actions, an override with no recorded reason, concepts not tied to the actual
research, technically incorrect explanations, an unnecessarily long curriculum, or
privacy over-collection. Return JSON only (findings: concern, detail, severity).

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
