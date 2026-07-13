"""The epistemic traffic light.

The colour of a claim is NOT assigned by a model's say-so. It is derived by
verifiable rules from the evidence attached to the claim: how much supporting vs
counter evidence, whether provenance exists, whether a result was reproduced, and
whether the claim was refuted or retracted.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EpistemicColor(str, Enum):
    GREEN = "GREEN"    # strong, traceable, reproduced
    YELLOW = "YELLOW"  # reasonable but incomplete / not replicated
    ORANGE = "ORANGE"  # plausible hypothesis / exploratory inference
    RED = "RED"        # speculation without sufficient validation
    BLACK = "BLACK"    # refuted, invalid, retracted, or contaminated


@dataclass(frozen=True)
class EvidenceProfile:
    """The verifiable inputs that determine a claim's colour."""

    supporting_evidence: int = 0
    counter_evidence: int = 0
    has_provenance: bool = False
    reproduced: bool = False
    refuted: bool = False
    retracted: bool = False
    contaminated: bool = False
    is_speculation: bool = False


@dataclass(frozen=True)
class ColorAssessment:
    color: EpistemicColor
    rationale: str


def assess_color(p: EvidenceProfile) -> ColorAssessment:
    """Rule-based colour assignment. Deterministic and auditable."""
    if p.refuted or p.retracted or p.contaminated:
        reason = "refuted" if p.refuted else "retracted" if p.retracted else "contaminated"
        return ColorAssessment(EpistemicColor.BLACK, f"Marked BLACK: {reason}.")

    if p.is_speculation or (p.supporting_evidence == 0 and not p.has_provenance):
        return ColorAssessment(
            EpistemicColor.RED,
            "Speculation or no supporting evidence/provenance.",
        )

    if not p.has_provenance:
        return ColorAssessment(
            EpistemicColor.RED, "Has evidence but lacks provenance; cannot be trusted."
        )

    # From here: has provenance and at least some support.
    if p.counter_evidence > p.supporting_evidence:
        return ColorAssessment(
            EpistemicColor.ORANGE,
            "Counter-evidence outweighs support; exploratory at best.",
        )

    if p.supporting_evidence >= 1 and not p.reproduced:
        return ColorAssessment(
            EpistemicColor.YELLOW,
            "Reasonable, provenance-backed evidence, but not yet reproduced.",
        )

    if p.reproduced and p.supporting_evidence >= 1 and p.counter_evidence == 0:
        return ColorAssessment(
            EpistemicColor.GREEN,
            "Strong: provenance-backed, reproduced, no outstanding counter-evidence.",
        )

    if p.reproduced and p.counter_evidence > 0:
        return ColorAssessment(
            EpistemicColor.YELLOW,
            "Reproduced but has some counter-evidence; not fully settled.",
        )

    return ColorAssessment(EpistemicColor.ORANGE, "Insufficient basis for a stronger colour.")
