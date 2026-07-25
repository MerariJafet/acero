"""Novelty taxonomy and a computable ContributionScore.

The reviewer makes two sharp points:

1. "Not found" ≠ "new". A result may already exist in supplements, theses, proceedings,
   patents, preprints, trial registries, institutional repos, another language, or as an
   unpublished negative. So bibliographic novelty must come with a CONFIDENCE that scales
   with how many source families were actually searched.

2. There are FOUR kinds of novelty — bibliographic, of data, methodological, and
   scientific — and only the last (changing what we believe) is what matters most and is
   hardest. A brand-new but trivial correlation is high-novelty and near-zero value.

ContributionScore = novelty × evidential_strength × scientific_importance × robustness ×
mechanistic_value. Being a product, any near-zero factor collapses the score — which is
exactly the discipline needed to stop "a very sophisticated machine for finding tiny
results".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NoveltyType(str, Enum):
    BIBLIOGRAPHIC = "bibliographic"   # no equivalent claim found
    DATA = "data"                     # nobody seems to have combined these datasets
    METHODOLOGICAL = "methodological"  # a new method is applied
    SCIENTIFIC = "scientific"         # changes what we believe about the phenomenon


class SourceFamily(str, Enum):
    PEER_REVIEWED = "peer_reviewed"
    PREPRINT = "preprint"
    THESIS = "thesis"
    CONFERENCE = "conference"
    PATENT = "patent"
    TRIAL_REGISTRY = "trial_registry"
    INSTITUTIONAL_REPO = "institutional_repo"
    OTHER_LANGUAGE = "other_language"
    NEGATIVE_UNPUBLISHED = "negative_unpublished"
    SPECIALIZED_DB = "specialized_db"


_ALL_FAMILIES = tuple(SourceFamily)


@dataclass
class BibliographicNovelty:
    novelty: float          # 0 (already exists) … 1 (no equivalent found)
    confidence: float       # scaled by how many source families were searched
    coverage: float
    caveat: str


def bibliographic_novelty(found_equivalent: bool,
                          searched: set[SourceFamily]) -> BibliographicNovelty:
    """'Not found' only means 'novel' to the extent we actually looked. Confidence is
    the fraction of source families searched — capped so an unindexed corpus can never
    masquerade as proof of novelty."""
    coverage = len(searched) / len(_ALL_FAMILIES)
    if found_equivalent:
        return BibliographicNovelty(0.0, 1.0, coverage,
                                    "existe una afirmación equivalente")
    caveat = ("cobertura de fuentes limitada: 'no encontrado' no es 'nuevo'"
              if coverage < 0.6 else "búsqueda amplia de fuentes")
    return BibliographicNovelty(1.0, round(coverage, 3), round(coverage, 3), caveat)


@dataclass
class ContributionComponents:
    """Each factor in [0,1]. Defaults are deliberately conservative (mid/low)."""
    novelty: float = 0.0                # strongest of the four novelty types, weighted
    evidential_strength: float = 0.0    # from independence/regime (0 assoc … 1 replicated)
    scientific_importance: float = 0.0  # would it change a theory/decision?
    robustness: float = 0.0             # survives sensitivity/nulls/subsets
    mechanistic_value: float = 0.0      # explains a mechanism vs bare correlation

    def clamped(self) -> ContributionComponents:
        c = lambda v: max(0.0, min(1.0, v))  # noqa: E731
        return ContributionComponents(
            c(self.novelty), c(self.evidential_strength), c(self.scientific_importance),
            c(self.robustness), c(self.mechanistic_value))


def weighted_novelty(types: dict[NoveltyType, float]) -> float:
    """Scientific novelty dominates; bibliographic alone is the weakest signal."""
    w = {NoveltyType.BIBLIOGRAPHIC: 0.15, NoveltyType.DATA: 0.20,
         NoveltyType.METHODOLOGICAL: 0.25, NoveltyType.SCIENTIFIC: 0.40}
    num = sum(w[t] * max(0.0, min(1.0, v)) for t, v in types.items())
    den = sum(w[t] for t in types) or 1.0
    return num / den


def contribution_score(c: ContributionComponents) -> float:
    """Product of the five factors: a near-zero factor collapses the contribution."""
    c = c.clamped()
    return (c.novelty * c.evidential_strength * c.scientific_importance
            * c.robustness * c.mechanistic_value)


def contribution_band(score: float) -> str:
    if score >= 0.5:
        return "mayor"
    if score >= 0.2:
        return "notable"
    if score >= 0.05:
        return "menor"
    return "trivial"


@dataclass
class ContributionReport:
    components: ContributionComponents
    score: float
    band: str
    bibliographic: BibliographicNovelty | None = None

    def summary(self) -> dict[str, object]:
        return {"score": round(self.score, 4), "band": self.band,
                "components": vars(self.components.clamped()),
                "bibliographic_caveat":
                    self.bibliographic.caveat if self.bibliographic else None}


def assess(components: ContributionComponents,
           bibliographic: BibliographicNovelty | None = None) -> ContributionReport:
    s = contribution_score(components)
    return ContributionReport(components, s, contribution_band(s), bibliographic)
