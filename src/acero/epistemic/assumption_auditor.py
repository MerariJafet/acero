"""F3 — Assumption auditor: which assumptions the claim depends on, and how hard.

For each declared assumption: is it validated? by what evidence? how sensitive is the
conclusion to it (would the claim change if the assumption failed)? An unvalidated,
high-sensitivity assumption is the most dangerous kind — the whole claim rests on it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .claim_reconstructor import ClaimRecord


@dataclass
class AssumptionAudit:
    assumption: str
    validated: bool
    evidence: str
    sensitivity: float        # 0 (claim robust to it) .. 1 (claim rests entirely on it)
    status: str

    @property
    def critical(self) -> bool:
        return not self.validated and self.sensitivity >= 0.6


def audit_assumptions(claim: ClaimRecord,
                      validated: set[str] | None = None,
                      sensitivities: dict[str, float] | None = None
                      ) -> list[AssumptionAudit]:
    """Audit each declared assumption. `validated`/`sensitivities` can be supplied by an
    expert or a literature check; defaults are conservative (unvalidated, medium-high)."""
    val = validated or set()
    sens = sensitivities or {}
    out: list[AssumptionAudit] = []
    for a in claim.assumptions:
        is_val = a in val
        s = float(sens.get(a, 0.6))
        out.append(AssumptionAudit(
            assumption=a, validated=is_val,
            evidence="verificado" if is_val else "sin verificación directa",
            sensitivity=s,
            status="crítico" if (not is_val and s >= 0.6) else
                   ("ok" if is_val else "revisar")))
    out.sort(key=lambda x: (-int(x.critical), -x.sensitivity))
    return out


def critical_assumptions(audits: list[AssumptionAudit]) -> list[AssumptionAudit]:
    return [a for a in audits if a.critical]
