"""Build separate explanation levels for a scientific result.

The five levels are DISTINCT artifacts (intuition, conceptual, mathematical,
computational, frontier). Every level must carry its limitations; technical claims
reference real equations/code/evidence in the record. Codex may draft the prose, but the
structured facts (equations, code refs, evidence refs, limitations) come from the
record, never invented, and an abstention is always given a concrete reason.
"""

from __future__ import annotations

from typing import Any

from ..models import ExplainMode, ExplanationArtifact, ExplanationLevel


def build_levels(
    subject: str,
    *,
    phenomenon: str,
    variables: list[str],
    mechanism: str,
    assumptions: list[str],
    equations: list[str],
    code_references: list[str],
    evidence_references: list[str],
    limitations: list[str],
    alternatives: list[str] | None = None,
    known: list[str] | None = None,
    unknown: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> list[ExplanationArtifact]:
    """Return one ExplanationArtifact per level, all sharing the record's facts.

    ``limitations`` must be non-empty — a level with no stated limitation is not allowed.
    """
    if not limitations:
        raise ValueError("every explanation must state at least one limitation")
    prov = provenance or {"author": "acero", "source": "record"}
    alt = alternatives or []

    intuition = ExplanationArtifact(
        subject=subject, level=ExplanationLevel.INTUITION,
        content=(f"Phenomenon: {phenomenon}. Core idea: {mechanism}. "
                 f"Think of it loosely as an analogy with clear limits — see limitations."),
        limitations=limitations,
        questions=[f"In your own words, what changes {variables[0] if variables else 'the output'}?"],
        provenance=prov)

    conceptual = ExplanationArtifact(
        subject=subject, level=ExplanationLevel.CONCEPTUAL,
        content=(f"Variables: {', '.join(variables)}. Proposed mechanism: {mechanism}. "
                 f"Assumptions: {'; '.join(assumptions) or 'none stated'}. "
                 f"Alternatives considered: {'; '.join(alt) or 'none'}."),
        limitations=limitations,
        questions=["Which assumption, if wrong, would most change the conclusion?"],
        provenance=prov)

    mathematical = ExplanationArtifact(
        subject=subject, level=ExplanationLevel.MATHEMATICAL,
        content=("The governing relations, with units and uncertainty. Coefficients are "
                 "point estimates unless an interval is given."),
        equations=equations,
        limitations=limitations + ["coefficients without calibrated intervals are point estimates"],
        questions=["Which term depends on the library we imposed?"],
        provenance=prov)

    computational = ExplanationArtifact(
        subject=subject, level=ExplanationLevel.COMPUTATIONAL,
        content=("Data, algorithms, parameters, tests and reproducibility for this result."),
        code_references=code_references, evidence_references=evidence_references,
        limitations=limitations,
        questions=["What would you change in the code to test sensitivity to noise?"],
        provenance=prov)

    frontier = ExplanationArtifact(
        subject=subject, level=ExplanationLevel.FRONTIER,
        content=(f"Known: {'; '.join(known or []) or 'stated in record'}. "
                 f"Not known: {'; '.join(unknown or []) or 'see limitations'}. "
                 f"Open disagreements and next experiments."),
        limitations=limitations,
        questions=["What is the single measurement that would most reduce uncertainty?"],
        provenance=prov)

    return [intuition, conceptual, mathematical, computational, frontier]


def explain_mode(mode: ExplainMode, *, reasons: dict[str, list[str]]) -> str:
    """Answer an EXPLAIN_* query from structured reasons in the record.

    ``reasons`` maps a mode key to concrete bullet reasons. For EXPLAIN_ABSTENTION the
    answer must be a specific cause (data insufficient, equivalent models, non-identifiable
    parameter, unstable derivatives, missing evidence, experiment required) — never merely
    "confidence was low".
    """
    key = mode.value
    bullets = reasons.get(key) or reasons.get(mode.name) or []
    if mode == ExplainMode.EXPLAIN_ABSTENTION and not bullets:
        raise ValueError("abstention must be explained with a concrete cause, not 'low confidence'")
    if not bullets:
        return f"{key}: no structured reasons recorded."
    return f"{key}:\n" + "\n".join(f"  - {b}" for b in bullets)
