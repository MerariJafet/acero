"""F2 — Evidence lineage: how many INDEPENDENT evidence lines really support a claim.

The reviewer: five papers can all depend on the same dataset or experimental root and thus
NOT be five independent pieces of evidence. This module traces, for each claim, the chain
observation → dataset → experiment → lab → instrument → pipeline → replications →
retractions, and collapses evidence that shares a provenance root into a single line. It
reuses the IndependenceGraph so "independent evidence" means the same thing everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..science.independence_graph import (
    DatasetProvenance,
    IndependenceGraph,
    IndependenceKind,
)


@dataclass
class EvidenceItem:
    """One reported piece of evidence and its full provenance."""
    evidence_id: str
    claim_id: str
    source: str = ""                 # paper / DOI
    dataset_id: str = ""
    study_id: str = ""
    laboratory: str = ""
    instrument: str = ""
    pipeline: str = ""
    cohort: str = ""
    period: str = ""
    provenance_root: str = ""
    supports: bool = True            # supports (True) or weakens (False) the claim
    retracted: bool = False

    def to_provenance(self) -> DatasetProvenance:
        return DatasetProvenance(
            dataset_id=self.dataset_id or self.evidence_id,
            study_id=self.study_id, laboratory=self.laboratory,
            instrument=self.instrument, cohort=self.cohort, period=self.period,
            curation_pipeline=self.pipeline, provenance_root=self.provenance_root,
            assay_source=self.study_id)


@dataclass
class EvidenceLineage:
    """The evidence graph behind one claim."""
    claim_id: str
    items: list[EvidenceItem] = field(default_factory=list)

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)

    def _active(self) -> list[EvidenceItem]:
        return [e for e in self.items if not e.retracted]

    def n_reported(self) -> int:
        return len(self._active())

    def independent_lines(self) -> list[list[EvidenceItem]]:
        """Group evidence into genuinely independent lines: two items whose provenance the
        IndependenceGraph does NOT deem independent go in the same line (one evidence)."""
        active = [e for e in self._active() if e.supports]
        g = IndependenceGraph()
        for e in active:
            g.add(e.to_provenance())
        lines: list[list[EvidenceItem]] = []
        for e in active:
            placed = False
            for line in lines:
                rep = line[0]
                v = g.independence(e.to_provenance().dataset_id,
                                   rep.to_provenance().dataset_id)
                if v.kind < IndependenceKind.DIFF_COHORT:   # not independent enough
                    line.append(e)
                    placed = True
                    break
            if not placed:
                lines.append([e])
        return lines

    def n_independent(self) -> int:
        return len(self.independent_lines())

    def contradicting(self) -> list[EvidenceItem]:
        return [e for e in self._active() if not e.supports]

    def retractions(self) -> list[EvidenceItem]:
        return [e for e in self.items if e.retracted]

    def summary(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "reported_evidence": self.n_reported(),
            "independent_lines": self.n_independent(),
            "inflation": self.n_reported() - self.n_independent(),
            "contradicting": len(self.contradicting()),
            "retracted": len(self.retractions()),
            "note": ("varias evidencias comparten raíz de procedencia → cuentan como una"
                     if self.n_reported() > self.n_independent() else
                     "cada evidencia es una línea independiente"),
        }
