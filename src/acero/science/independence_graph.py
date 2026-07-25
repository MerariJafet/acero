"""IndependenceGraph — independence COMPUTED from provenance, never declared.

The reviewer's sharpest point: a split of the same dataset is statistically separated but
NOT scientifically separated — it shares protocol, instrument, curation, selection bias,
chemical/observational distribution, labels and possible near-duplicates. So
CONFIRMADO_EN_HOLDOUT must never be promoted to REPLICADO_EN_DATASET_INDEPENDIENTE by
assertion. Independence has to be *derived* from what two datasets actually share.

This module records each dataset's provenance and computes the LEVEL of independence
between two datasets from the dimensions they share (study, assay/source, laboratory,
curation pipeline, provenance root, instrument, cohort, period). It also states, per pair,
which dimensions of independence do and do NOT hold — so the dossier is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class IndependenceKind(IntEnum):
    """Higher = more independent. The claim compiler keys 'replication' off these."""
    SAME_PARTITION = 0        # a split of the very same file
    SAME_STUDY = 1            # different files, same study/curation root
    SAME_SOURCE = 2           # same assay/source/repository, different study
    SAME_LAB = 3              # same laboratory, different source
    SAME_COHORT = 4           # same cohort, different lab
    DIFF_COHORT = 5           # different cohort
    DIFF_INSTRUMENT = 6       # different instrument/protocol
    DIFF_SOURCE = 7           # different source/repository entirely
    EXTERNAL_REPLICATION = 8  # independent by every recorded dimension


# the minimum kind that counts as a genuinely independent dataset for a strong claim
INDEPENDENT_DATASET_MIN = IndependenceKind.DIFF_COHORT


@dataclass(frozen=True)
class DatasetProvenance:
    dataset_id: str
    study_id: str = ""
    assay_source: str = ""          # e.g. "caco2_wang", "GEO", assay id
    repository: str = ""            # e.g. "dataverse.harvard.edu"
    laboratory: str = ""
    instrument: str = ""
    cohort: str = ""
    period: str = ""
    curation_pipeline: str = ""
    provenance_root: str = ""       # the ultimate upstream origin
    is_partition_of: str = ""       # dataset_id this was split from (holdout!)


@dataclass
class PairVerdict:
    kind: IndependenceKind
    shares: list[str] = field(default_factory=list)
    differs: list[str] = field(default_factory=list)

    @property
    def is_independent_dataset(self) -> bool:
        return self.kind >= INDEPENDENT_DATASET_MIN

    @property
    def is_replication_capable(self) -> bool:
        """Enough independence that agreeing evidence counts as replication (not reuse)."""
        return self.kind >= INDEPENDENT_DATASET_MIN

    def explain(self) -> str:
        return (f"{self.kind.name} | comparten: {', '.join(self.shares) or '—'} | "
                f"difieren: {', '.join(self.differs) or '—'}")


class IndependenceGraph:
    """Holds dataset provenance and computes pairwise independence."""

    def __init__(self) -> None:
        self._prov: dict[str, DatasetProvenance] = {}

    def add(self, prov: DatasetProvenance) -> None:
        self._prov[prov.dataset_id] = prov

    def get(self, dataset_id: str) -> DatasetProvenance | None:
        return self._prov.get(dataset_id)

    def _shares_root(self, a: DatasetProvenance, b: DatasetProvenance) -> bool:
        return bool(a.provenance_root and a.provenance_root == b.provenance_root)

    def independence(self, a_id: str, b_id: str) -> PairVerdict:
        a, b = self._prov.get(a_id), self._prov.get(b_id)
        if a is None or b is None:
            return PairVerdict(IndependenceKind.SAME_STUDY,
                               shares=["procedencia desconocida (conservador)"])
        # partition relationship (holdout of the same file) — the hard case
        if a.is_partition_of == b_id or b.is_partition_of == a_id \
                or (a.is_partition_of and a.is_partition_of == b.is_partition_of):
            return PairVerdict(IndependenceKind.SAME_PARTITION,
                               shares=["misma partición / mismo archivo de origen"])

        shares: list[str] = []
        differs: list[str] = []

        def cmp(field_name: str, label: str) -> bool:
            va, vb = getattr(a, field_name), getattr(b, field_name)
            if va and vb and va == vb:
                shares.append(label)
                return True
            if va and vb and va != vb:
                differs.append(label)
            return False

        same_study = cmp("study_id", "estudio")
        same_root = self._shares_root(a, b)
        if same_root:
            shares.append("raíz de procedencia")
        same_source = cmp("assay_source", "assay/fuente") or cmp("repository", "repositorio")
        same_lab = cmp("laboratory", "laboratorio")
        same_cohort = cmp("cohort", "cohorte")
        cmp("instrument", "instrumento")
        cmp("period", "periodo")
        cmp("curation_pipeline", "pipeline de curación")

        # classify from the strongest thing they still share
        if same_study or same_root:
            kind = IndependenceKind.SAME_STUDY
        elif same_source:
            kind = IndependenceKind.SAME_SOURCE
        elif same_lab:
            kind = IndependenceKind.SAME_LAB
        elif same_cohort:
            kind = IndependenceKind.SAME_COHORT
        elif a.cohort and b.cohort and a.cohort != b.cohort:
            kind = IndependenceKind.DIFF_COHORT
            if a.instrument and b.instrument and a.instrument != b.instrument:
                kind = IndependenceKind.DIFF_INSTRUMENT
            if a.assay_source and b.assay_source and a.assay_source != b.assay_source:
                kind = IndependenceKind.DIFF_SOURCE
        elif not shares:
            kind = IndependenceKind.EXTERNAL_REPLICATION
        else:
            kind = IndependenceKind.SAME_SOURCE
        return PairVerdict(kind, shares, differs)

    def is_replication(self, a_id: str, b_id: str) -> bool:
        """The rule: agreeing evidence across a,b counts as replication ONLY if the
        graph says they are independent enough — a split never qualifies."""
        return self.independence(a_id, b_id).is_replication_capable
