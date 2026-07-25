"""F4 — Question portfolio: a DIVERSIFIED, traceable set of high-value questions.

Not a ranked list dominated by one family. The portfolio caps how many questions come from
any single family (so a topic isn't attacked from only one angle) and keeps each question's
genealogy: question → target vulnerability → claim. Only gate-passing questions enter.
"""

from __future__ import annotations

from dataclasses import dataclass

from .question_engine import RankedQuestion


@dataclass
class PortfolioEntry:
    ranked: RankedQuestion
    lineage: dict[str, str]        # question_id → vulnerability → claim

    @property
    def priority(self) -> float:
        return self.ranked.priority


def build_portfolio(ranked: list[RankedQuestion], *, max_per_family: int = 2,
                    size: int = 8) -> list[PortfolioEntry]:
    """Diversify across question families; keep genealogy; only passed questions."""
    passed = [r for r in ranked if r.verdict.passed]
    passed.sort(key=lambda r: -r.priority)
    per_family: dict[str, int] = {}
    out: list[PortfolioEntry] = []
    for r in passed:
        fam = r.question.family.value
        if per_family.get(fam, 0) >= max_per_family:
            continue
        per_family[fam] = per_family.get(fam, 0) + 1
        out.append(PortfolioEntry(r, {
            "question_id": r.question.question_id,
            "target_vulnerability": r.question.target_vulnerability,
            "origin": r.question.origin,
            "known_context": r.question.known_context[:100]}))
        if len(out) >= size:
            break
    return out


def family_coverage(portfolio: list[PortfolioEntry]) -> set[str]:
    return {e.ranked.question.family.value for e in portfolio}
