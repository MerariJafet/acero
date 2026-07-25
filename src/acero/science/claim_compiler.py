"""Claim Compiler — translate evidence into the MAXIMUM claim it is allowed to make.

The reviewer: an observational analysis may say "associated with"; an external
prediction "predicts in this population"; an identifiable causal design "effect estimated
under these assumptions"; an independent replication "replicated in…"; and NEVER
"demonstrated / proven / discovered" without the conditions being met.

This module (a) computes the ceiling claim from an evidence profile, and (b) SCANS a
draft dossier for language that exceeds that ceiling — turning honesty from a guideline
into a lint rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum

from .independence import EvidenceStrength, IndependenceLedger
from .preregistration import Regime


class ClaimLevel(IntEnum):
    NONE = 0
    ASSOCIATION = 1              # "asociado con"
    PREDICTION = 2               # "predice en la población X"
    CAUSAL_UNDER_ASSUMPTIONS = 3  # "efecto estimado bajo los supuestos Z"
    REPLICATED = 4               # "replicado en un conjunto independiente"


_CLAIM_TEMPLATES = {
    ClaimLevel.NONE: "sin evidencia suficiente para afirmar nada",
    ClaimLevel.ASSOCIATION: "{x} está ASOCIADO con {y} (análisis observacional)",
    ClaimLevel.PREDICTION: "{x} PREDICE {y} en la población evaluada (validación externa)",
    ClaimLevel.CAUSAL_UNDER_ASSUMPTIONS:
        "efecto de {x} sobre {y} ESTIMADO BAJO LOS SUPUESTOS declarados",
    ClaimLevel.REPLICATED:
        "asociación entre {x} y {y} REPLICADA en un conjunto independiente",
}

# design of the study that produced the evidence
DESIGN_OBSERVATIONAL = "observational"
DESIGN_PREDICTIVE_EXTERNAL = "predictive_external"   # validated on a real holdout
DESIGN_CAUSAL = "causal"                             # a causal-identification design


@dataclass
class EvidenceProfile:
    exposure: str
    outcome: str
    regime: Regime
    design: str = DESIGN_OBSERVATIONAL
    causal_identifiable: bool = False
    independence: IndependenceLedger | None = None
    has_null_test: bool = True

    def _strength(self) -> EvidenceStrength:
        return self.independence.strength() if self.independence else EvidenceStrength.NONE


def max_claim(profile: EvidenceProfile) -> ClaimLevel:
    """The single strongest claim the evidence permits — nothing above it is allowed."""
    if not profile.has_null_test:
        return ClaimLevel.NONE                # no null test → not even association
    level = ClaimLevel.ASSOCIATION
    if profile.design == DESIGN_PREDICTIVE_EXTERNAL and \
            (profile.independence and profile.independence.has_independent_dataset()):
        level = ClaimLevel.PREDICTION
    if profile.design == DESIGN_CAUSAL and profile.causal_identifiable:
        level = ClaimLevel.CAUSAL_UNDER_ASSUMPTIONS
    # replication is the strongest, but only under a confirmation regime with STRONG
    # (methodologically-different AND independent-dataset) agreement
    if profile.regime is Regime.CONFIRMATION and \
            profile._strength() is EvidenceStrength.STRONG:
        level = max(level, ClaimLevel.REPLICATED)
    return level


def compile_claim(profile: EvidenceProfile) -> str:
    lvl = max_claim(profile)
    return _CLAIM_TEMPLATES[lvl].format(x=profile.exposure, y=profile.outcome)


# words that assert more than ACERO may ever say, or that need specific conditions
@dataclass
class OverclaimViolation:
    phrase: str
    reason: str


# (regex, human reason, predicate(profile)->allowed)
_BANNED = [
    (r"\bdescubr\w+|\bhallazgo confirmad\w+", "ACERO nunca declara descubrimiento (techo: candidato a revisión)",
     lambda p: False),
    (r"\bdemuestr\w+|\bprueba que\b|\bqueda demostrad\w+|\bestablece que\b",
     "'demostrar/probar' exige replicación independiente fuerte en régimen de confirmación",
     lambda p: p.regime is Regime.CONFIRMATION and p._strength() is EvidenceStrength.STRONG),
    (r"\bconfirmad\w+|\bconfirma que\b",
     "'confirmar' exige régimen de confirmación (protocolo congelado + holdout)",
     lambda p: p.regime is Regime.CONFIRMATION),
    (r"\bcausa\b|\bcausal\w*|\bprovoca\b|\bproduce (?:un|el)\b",
     "lenguaje causal exige un diseño de identificación causal válido",
     lambda p: p.design == DESIGN_CAUSAL and p.causal_identifiable),
]


def scan_overclaims(text: str, profile: EvidenceProfile) -> list[OverclaimViolation]:
    """Return every phrase in the draft that exceeds what the evidence permits."""
    out: list[OverclaimViolation] = []
    low = text.lower()
    for pattern, reason, allowed in _BANNED:
        for m in re.finditer(pattern, low):
            if not allowed(profile):
                out.append(OverclaimViolation(m.group(0), reason))
    return out
