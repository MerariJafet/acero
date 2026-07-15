"""Scientific reliability scorecard, readiness levels, and publication candidate.

There is NO single magic trust score. A ScientificReliabilityCard reports each dimension
separately with its measurement, sample, version, limitation, trend, and threshold. Readiness
is a ladder that tops out at READY_FOR_HUMAN_SCIENTIFIC_REVIEW — `DISCOVERY_CONFIRMED` does
not exist and is never implemented. A PublicationCandidate PREPARES; it never publishes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso


@dataclass
class Dimension:
    name: str
    measurement: float | None                # None = not measured / insufficient
    sample: int
    version: str = "v1"
    limitation: str = ""
    trend: str = "flat"                       # up | down | flat | unknown
    threshold: float = 0.7

    @property
    def meets_threshold(self) -> bool:
        return self.measurement is not None and self.measurement >= self.threshold

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "measurement": self.measurement, "sample": self.sample,
                "version": self.version, "limitation": self.limitation, "trend": self.trend,
                "threshold": self.threshold, "meets_threshold": self.meets_threshold}


DIMENSION_NAMES = (
    "reproducibility", "calibration", "evidence_independence", "adversarial_robustness",
    "numerical_stability", "domain_validity", "human_understanding", "gate_compliance",
    "provenance_completeness", "unresolved_contradictions", "abstention_quality",
)


@dataclass
class ScientificReliabilityCard:
    subject: str
    dimensions: dict[str, Dimension] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def set(self, name: str, measurement: float | None, sample: int, *,
            limitation: str = "", trend: str = "unknown", threshold: float = 0.7,
            version: str = "v1") -> None:
        if name not in DIMENSION_NAMES:
            raise KeyError(f"unknown reliability dimension {name!r}")
        self.dimensions[name] = Dimension(name, measurement, sample, version, limitation,
                                          trend, threshold)

    def measured_dimensions(self) -> list[Dimension]:
        return [d for d in self.dimensions.values() if d.measurement is not None]

    def unmet(self) -> list[str]:
        return [d.name for d in self.dimensions.values() if not d.meets_threshold]

    def as_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "created_at": self.created_at,
                "dimensions": {n: d.as_dict() for n, d in self.dimensions.items()},
                "unmet": self.unmet()}


class ReadinessLevel(str, Enum):
    NOT_READY = "NOT_READY"
    EXPLORATORY = "EXPLORATORY"
    COMPUTATIONALLY_REPRODUCIBLE = "COMPUTATIONALLY_REPRODUCIBLE"
    METHODOLOGICALLY_REVIEWED = "METHODOLOGICALLY_REVIEWED"
    ADVERSARIALLY_TESTED = "ADVERSARIALLY_TESTED"
    EXTERNALLY_VALIDATED = "EXTERNALLY_VALIDATED"
    READY_FOR_HUMAN_SCIENTIFIC_REVIEW = "READY_FOR_HUMAN_SCIENTIFIC_REVIEW"
    # NOTE: DISCOVERY_CONFIRMED intentionally does not exist.


def assess_readiness(card: ScientificReliabilityCard, *, gate_complete: bool,
                     human_understands: bool, externally_validated: bool = False,
                     unresolved_contradictions: int = 0) -> tuple[ReadinessLevel, list[str]]:
    """Climb the ladder only as far as the evidence supports; list the blockers."""
    blockers: list[str] = []
    d = card.dimensions

    def ok(name: str) -> bool:
        return name in d and d[name].meets_threshold

    if not ok("reproducibility"):
        blockers.append("not computationally reproducible")
        return ReadinessLevel.EXPLORATORY, blockers
    level = ReadinessLevel.COMPUTATIONALLY_REPRODUCIBLE

    if ok("provenance_completeness") and ok("domain_validity"):
        level = ReadinessLevel.METHODOLOGICALLY_REVIEWED
    else:
        blockers.append("methodology/provenance incomplete")

    if ok("adversarial_robustness") and ok("evidence_independence") and ok("calibration"):
        level = ReadinessLevel.ADVERSARIALLY_TESTED
    else:
        blockers.append("adversarial/independence/calibration below threshold")

    if externally_validated:
        level = ReadinessLevel.EXTERNALLY_VALIDATED
    else:
        blockers.append("no external validation")

    if unresolved_contradictions > 0:
        blockers.append(f"{unresolved_contradictions} unresolved contradiction(s)")
    if not gate_complete:
        blockers.append("gate compliance incomplete")
    if not human_understands:
        blockers.append("human comprehension of central claim insufficient")

    if (level == ReadinessLevel.EXTERNALLY_VALIDATED and gate_complete
            and human_understands and unresolved_contradictions == 0):
        level = ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW
    return level, blockers


@dataclass
class PublicationCandidate:
    """Prepares an artifact for HUMAN review — never publishes automatically."""

    project: str
    central_claim: str
    evidence: list[str] = field(default_factory=list)
    reliability_card: ScientificReliabilityCard | None = None
    replication_status: str = "REEXECUTION"
    unresolved_issues: list[str] = field(default_factory=list)
    human_understanding_status: str = "unknown"
    gate_status: str = "incomplete"
    readiness: ReadinessLevel = ReadinessLevel.NOT_READY
    blockers: list[str] = field(default_factory=list)
    required_external_review: bool = True

    def evaluate(self, *, gate_complete: bool, human_understands: bool,
                 externally_validated: bool = False,
                 unresolved_contradictions: int = 0) -> ReadinessLevel:
        if self.reliability_card is None:
            self.readiness = ReadinessLevel.NOT_READY
            self.blockers = ["no reliability card"]
            return self.readiness
        level, blockers = assess_readiness(
            self.reliability_card, gate_complete=gate_complete,
            human_understands=human_understands, externally_validated=externally_validated,
            unresolved_contradictions=unresolved_contradictions)
        self.readiness = level
        self.blockers = blockers + self.unresolved_issues
        self.gate_status = "complete" if gate_complete else "incomplete"
        self.human_understanding_status = "sufficient" if human_understands else "insufficient"
        return level

    @property
    def can_publish_automatically(self) -> bool:
        """Always False. Publication is never automatic (constitution rule 11)."""
        return False

    def as_dict(self) -> dict[str, Any]:
        return {"project": self.project, "central_claim": self.central_claim,
                "readiness": self.readiness.value, "blockers": self.blockers,
                "replication_status": self.replication_status,
                "gate_status": self.gate_status,
                "human_understanding_status": self.human_understanding_status,
                "required_external_review": self.required_external_review,
                "can_publish_automatically": self.can_publish_automatically}
