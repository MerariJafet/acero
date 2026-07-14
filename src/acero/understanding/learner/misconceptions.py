"""Misconception detection and resolution.

Detects the classic confusions of computational science. A misconception is NOT resolved
by an explanation alone — resolution requires a NEW passing piece of understanding
evidence that specifically contradicts the confusion. The same error re-appearing in a
different context re-opens it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Criticality, Misconception, UnderstandingEvidence

_NEGATORS = ("not ", "n't", "never", "isn't", "does not", "doesn't", "cannot",
             "is not", "are not")


@dataclass(frozen=True)
class MisconceptionPattern:
    key: str
    concept: str
    statement: str            # the WRONG belief, stated plainly
    severity: Criticality
    # regexes (lowercased) that, when matched in a learner's response, signal the error
    triggers: tuple[str, ...]
    corrective_activity: str


# The canonical confusions ACERO must catch. Triggers are deliberately conservative
# (they look for the *conflation*, not merely the words) to avoid false positives.
CATALOG: tuple[MisconceptionPattern, ...] = (
    MisconceptionPattern(
        "correlation_causation", "causality",
        "correlation proves causation", Criticality.HIGH,
        (r"correlat\w+.*(prov|mean|imply|show)\w*.*caus",
         r"because.*correlat\w+.*caus"),
        "identify a confounder that could produce the correlation without causation"),
    MisconceptionPattern(
        "fit_equals_mechanism", "system_identification",
        "a good fit means the true mechanism was found", Criticality.HIGH,
        (r"(best|good|low rmse|lowest error|r2).*(therefore|so|means).*(true|real|correct) "
         r"(mechanism|model|law)",
         r"fits best.*(is|must be).*(true|correct|right)"),
        "show two models with equal fit but different mechanisms"),
    MisconceptionPattern(
        "model_confidence_is_certainty", "calibration",
        "high model confidence means high scientific certainty", Criticality.HIGH,
        (r"(high|large).*confidence.*(means|so|therefore).*(certain|true|proven)",),
        "compare an uncalibrated confidence score with empirical frequency"),
    MisconceptionPattern(
        "simulation_is_proof", "evidence",
        "a simulation proves a physical fact", Criticality.HIGH,
        (r"simulat\w+.*(prov|demonstrat|confirm)\w*.*(physical|real|true)",),
        "state what a simulation can and cannot establish physically"),
    MisconceptionPattern(
        "absence_of_evidence", "evidence",
        "finding no evidence proves absence", Criticality.HIGH,
        (r"(no|didn.?t find|couldn.?t find).*evidence.*(prov|means|shows).*(no|absen|doesn)",
         r"absence of evidence.*evidence of absence"),
        "distinguish 'not detected' from 'shown to be absent' given power"),
    MisconceptionPattern(
        "recovering_equation_is_law", "governing_structure",
        "recovering an equation from data discovers a law", Criticality.HIGH,
        (r"recover\w+.*equation.*(is|means).*(law|discover)",
         r"found the (equation|formula).*(so|therefore).*(law|discover)"),
        "explain the imposed library and why a fit is not a law"),
    MisconceptionPattern(
        "analogy_is_equivalence", "analogy",
        "an analogy means physical equivalence", Criticality.MEDIUM,
        (r"analog\w+.*(is|means|proves).*(same|equivalent|identical)",),
        "state where the analogy breaks (regime of validity)"),
    MisconceptionPattern(
        "pvalue_truth", "statistics",
        "a low p-value means the hypothesis is true", Criticality.HIGH,
        (r"p.?value.*(low|small|<).*(means|so|therefore).*(true|proven|correct)",),
        "explain what a p-value is and is not"),
    MisconceptionPattern(
        "reproducible_is_correct", "reproducibility",
        "reproducible means correct", Criticality.MEDIUM,
        (r"reproducib\w+.*(means|so|therefore).*(correct|true|right|valid)",),
        "give a reproducible-but-wrong example (systematic bias)"),
    MisconceptionPattern(
        "complex_is_deep", "modeling",
        "a more complex model is a deeper one", Criticality.MEDIUM,
        (r"(more )?complex\w*.*(model|equation).*(is|means|therefore).*(deep|better|true)",),
        "compare parsimony vs complexity and overfitting"),
    MisconceptionPattern(
        "real_data_is_causal", "evidence",
        "real data yields a causal conclusion", Criticality.HIGH,
        (r"real data.*(so|therefore|means).*(caus|mechanism)",),
        "explain why observational real data is not intervention"),
    MisconceptionPattern(
        "codex_is_evidence", "epistemics",
        "an LLM/Codex output is evidence", Criticality.HIGH,
        (r"(codex|the llm|the model said|gpt).*(is|as|counts as|proves).*(evidence|proof|true)",),
        "restate that LLM output is advisory and must be verified"),
    MisconceptionPattern(
        "periodicity_is_mechanism", "mechanism_vs_pattern",
        "a periodicity proves the underlying mechanism", Criticality.HIGH,
        (r"(period|cycle|11.?2|pattern)\w*.*(prov|means|demonstrat|show|confirm)\w*."
         r"*(mechanism|dynamo|cause|physical)",),
        "distinguish a pattern in data from the mechanism that produced it"),
)

_BY_KEY = {p.key: p for p in CATALOG}


def _negated(span_text: str) -> bool:
    """A matched conflation is a false positive if it is negated within its own span
    (e.g. 'an analogy does NOT mean the systems are identical')."""
    return any(neg in span_text for neg in _NEGATORS)


def detect(text: str, *, learner_id: str, concept_hint: str | None = None,
           source: str = "response") -> list[Misconception]:
    """Return misconceptions whose conflation pattern appears in ``text``.

    Negation-aware: a trigger that matches a *negated* statement (the learner correctly
    denying the conflation) does not fire.
    """
    low = " ".join(text.lower().split())
    out: list[Misconception] = []
    for p in CATALOG:
        fired = False
        for t in p.triggers:
            m = re.search(t, low)
            if m and not _negated(m.group(0)):
                fired = True
                break
        if fired:
            out.append(Misconception(
                learner_id=learner_id, concept=p.concept, statement=p.statement,
                detected_from=source, severity=p.severity,
                corrective_activity=p.corrective_activity))
    return out


def resolves(misc: Misconception, evidence: UnderstandingEvidence,
             *, pass_threshold: float = 0.7) -> bool:
    """A misconception is resolved only by NEW passing evidence on its concept.

    An explanation the learner merely read does not count; the evidence must be a
    performance task (any EvidenceType) scoring at/above threshold, tied to the concept,
    and must NOT itself re-trigger the same confusion.
    """
    if evidence.score < pass_threshold:
        return False
    if evidence.concept_id != misc.concept and misc.concept not in (evidence.concept_id,):
        return False
    reopened = detect(evidence.response, learner_id=misc.learner_id,
                      concept_hint=misc.concept)
    return not any(m.statement == misc.statement for m in reopened)


def severity_of(key: str) -> Criticality:
    return _BY_KEY[key].severity if key in _BY_KEY else Criticality.MEDIUM
