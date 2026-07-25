"""F4 — Knowledge landscape: what we think we know, and where the gaps are.

Before generating questions, map the topic: the reconstructed claims, the vulnerability
surface across all of them, and the resulting gaps. The landscape is the substrate the
question generator mines — questions come from GAPS, not from thin air.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..epistemic.claim_reconstructor import ClaimRecord
from ..epistemic.vulnerability import EpistemicVulnerability, scan_vulnerabilities


@dataclass
class KnowledgeLandscape:
    topic: str
    claims: list[ClaimRecord] = field(default_factory=list)

    def add_claim(self, claim: ClaimRecord) -> None:
        self.claims.append(claim)

    def vulnerability_surface(self) -> list[EpistemicVulnerability]:
        surface: list[EpistemicVulnerability] = []
        for c in self.claims:
            surface.extend(scan_vulnerabilities(c))
        surface.sort(key=lambda v: -v.priority)
        return surface

    def gaps(self) -> list[str]:
        """Distinct kinds of ignorance across the topic (dedup by vulnerability type)."""
        seen: set[str] = set()
        out: list[str] = []
        for v in self.vulnerability_surface():
            if v.type.value not in seen:
                seen.add(v.type.value)
                out.append(f"{v.type.value}: {v.description}")
        return out

    def summary(self) -> dict[str, object]:
        surf = self.vulnerability_surface()
        return {"topic": self.topic, "n_claims": len(self.claims),
                "n_vulnerabilities": len(surf), "n_distinct_gaps": len(self.gaps()),
                "top_gaps": self.gaps()[:5]}
