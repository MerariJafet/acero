"""F6 — Rival theory generator: never jump from a question to a single favourite.

For a selected question, produce the main hypothesis, the null, and AT LEAST two plausible
rival explanations, with shared and differential predictions. The differential predictions
are what a discriminating test will exploit. Rivals are seeded from the vulnerability the
question targets (confounding → the real factor is a covariate; ambiguous mechanism →
competing mechanisms; reverse causation → the arrow is flipped).
"""

from __future__ import annotations

from ..science.discrimination import RivalSet
from .claim_reconstructor import ClaimRecord
from .vulnerability import EpistemicVulnerability, VulnerabilityType


def generate_rivals(vuln: EpistemicVulnerability, claim: ClaimRecord,
                    confounder_candidates: tuple[str, ...] = (),
                    question_id: str = "") -> RivalSet:
    """Build a well-posed rival set (≥2 rivals + differential predictions)."""
    exp = claim.exposure_or_input or "la exposición"
    out = claim.outcome_or_prediction or "el outcome"
    qid = question_id or f"q.{vuln.vulnerability_id}"
    main = f"{exp} es el factor causal de {out}"
    null = "no hay efecto tras controles adecuados"

    rivals: list[str] = []
    diff: dict[str, str] = {main: f"el efecto de {exp} sobrevive a todos los ajustes"}

    if vuln.type in (VulnerabilityType.CONFOUNDING, VulnerabilityType.UNMEASURED_VARIABLES):
        cands = confounder_candidates or ("un tercer factor A", "un tercer factor B")
        for c in cands[:2]:
            r = f"el verdadero factor es {c}"
            rivals.append(r)
            diff[r] = f"el efecto desaparece al ajustar por {c}"
    elif vuln.type == VulnerabilityType.REVERSE_CAUSATION:
        r = f"la causalidad está invertida: {out} causa {exp}"
        rivals.append(r)
        diff[r] = "un orden temporal fijo rompe la asociación en la dirección propuesta"
        rivals.append("una causa común genera ambos")
        diff["una causa común genera ambos"] = "ajustar por la causa común elimina el efecto"
    elif vuln.type == VulnerabilityType.AMBIGUOUS_MECHANISM:
        alts = vuln.alternative_explanations or ("mecanismo alternativo 1",
                                                 "mecanismo alternativo 2")
        for a in alts[:2]:
            rivals.append(a)
            diff[a] = f"{a} predice un resultado distinto en la variable discriminante"
    else:
        rivals = [f"el efecto es un artefacto de {vuln.type.value}",
                  "el efecto es real pero de tamaño trivial"]
        diff[rivals[0]] = "el efecto desaparece al corregir el artefacto"
        diff[rivals[1]] = "el tamaño del efecto cae por debajo del umbral relevante"

    # guarantee at least two rivals
    while len(rivals) < 2:
        extra = f"explicación alternativa {len(rivals) + 1}"
        rivals.append(extra)
        diff[extra] = "predice algo distinto en la variable discriminante"

    return RivalSet(
        question_id=qid, main=main, null=null, rivals=tuple(rivals),
        shared_predictions=(f"existe una asociación observable entre {exp} y {out}",),
        differential_predictions=diff)
