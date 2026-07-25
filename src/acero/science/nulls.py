"""A catalog of STRUCTURE-PRESERVING nulls — one generic permutation is not enough.

The reviewer: an analysis can pass a naive label permutation and still be spurious if
there is temporal dependence, family/subject structure, batch, spatial or phylogenetic
autocorrelation, or repeated measures. A null must justify WHY its randomization
preserves the structure it needs to preserve; otherwise it manufactures significance.

This module (a) implements deterministic null generators for the tabular cases, and
(b) — most importantly — RECOMMENDS the right null family from the declared data
structure, and warns loudly when a plain permutation would be invalid (pseudoreplication,
autocorrelation inflation, batch confounding…).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class NullFamily(str, Enum):
    LABEL_PERMUTATION = "label_permutation"
    BLOCK_PERMUTATION = "block_permutation"
    SUBJECT_PERMUTATION = "subject_permutation"
    TEMPORAL_CIRCULAR = "temporal_circular_shift"
    MARGINAL_PRESERVING = "marginal_preserving"
    SPATIAL = "spatial_preserving"
    PHYLOGENETIC = "phylogenetic"
    NETWORK = "network_rewiring"
    INSTRUMENT = "instrument_null"
    SELECTION = "selection_null"
    SYNTHETIC = "synthetic_simulation"


_JUSTIFY = {
    NullFamily.LABEL_PERMUTATION: "intercambiabilidad simple: válida solo si las "
        "observaciones son i.i.d. bajo H0 (sin grupos, tiempo ni autocorrelación)",
    NullFamily.BLOCK_PERMUTATION: "permuta DENTRO de bloques: conserva la estructura "
        "de bloque/lote y solo aleatoriza lo intercambiable dentro de cada uno",
    NullFamily.SUBJECT_PERMUTATION: "permuta a nivel de sujeto (una etiqueta por "
        "sujeto): evita la pseudorreplicación de medidas repetidas",
    NullFamily.TEMPORAL_CIRCULAR: "desplazamiento circular: preserva la autocorrelación "
        "temporal de la serie mientras rompe la relación con la etiqueta",
    NullFamily.MARGINAL_PRESERVING: "permuta cada variable por separado: conserva las "
        "distribuciones marginales pero rompe la dependencia entre variables",
    NullFamily.SPATIAL: "aleatorización que preserva la autocorrelación espacial",
    NullFamily.PHYLOGENETIC: "modelo nulo que respeta la estructura filogenética",
    NullFamily.NETWORK: "recableado que preserva grado/estructura del grafo",
    NullFamily.INSTRUMENT: "nulo que reproduce el efecto sistemático del instrumento",
    NullFamily.SELECTION: "nulo que reproduce el mecanismo de selección de la muestra",
    NullFamily.SYNTHETIC: "universo sintético con efecto nulo conocido por construcción",
}


def justify(family: NullFamily) -> str:
    return _JUSTIFY[family]


# --- deterministic generators (seeded) --------------------------------------
def label_permutation(labels: list, seed: int = 0) -> list:
    rng = random.Random(seed)
    out = list(labels)
    rng.shuffle(out)
    return out


def block_permutation(labels: list, blocks: list, seed: int = 0) -> list:
    """Permute labels only WITHIN each block (batch/site) — cross-block structure kept."""
    rng = random.Random(seed)
    by_block: dict = {}
    for i, b in enumerate(blocks):
        by_block.setdefault(b, []).append(i)
    out = list(labels)
    for _b, idxs in by_block.items():
        vals = [labels[i] for i in idxs]
        rng.shuffle(vals)
        for i, v in zip(idxs, vals, strict=True):
            out[i] = v
    return out


def subject_permutation(subject_of_row: list, subject_label: dict, seed: int = 0) -> list:
    """One label per subject, permuted across subjects, broadcast back to rows.
    Prevents pseudoreplication: repeated rows of a subject keep a single (permuted) label."""
    rng = random.Random(seed)
    subjects = sorted(subject_label)
    perm = list(subjects)
    rng.shuffle(perm)
    remap = {s: subject_label[perm[i]] for i, s in enumerate(subjects)}
    return [remap[s] for s in subject_of_row]


def circular_shift(series: list, shift: int) -> list:
    """Circular shift preserves autocorrelation of a time series under the null."""
    n = len(series)
    if n == 0:
        return []
    k = shift % n
    return series[-k:] + series[:-k] if k else list(series)


@dataclass
class DataStructure:
    """Declared structure of the data — drives which null is valid."""
    has_groups: bool = False        # subjects / centers / repeated measures
    temporal: bool = False          # time-ordered with autocorrelation
    spatial: bool = False
    phylogenetic: bool = False
    network: bool = False
    batch: bool = False


@dataclass
class NullRecommendation:
    family: NullFamily
    justification: str
    warnings: list[str] = field(default_factory=list)


def recommend_null(structure: DataStructure) -> NullRecommendation:
    """Pick the valid null family and WARN when a plain permutation would inflate FPR."""
    warnings: list[str] = []
    if structure.temporal:
        warnings.append("hay dependencia temporal: una permutación simple infla los "
                        "falsos positivos → usa desplazamiento circular")
        fam = NullFamily.TEMPORAL_CIRCULAR
    elif structure.has_groups:
        warnings.append("hay estructura de sujeto/grupo: una permutación simple "
                        "pseudorreplica → permuta a nivel de sujeto")
        fam = NullFamily.SUBJECT_PERMUTATION
    elif structure.batch:
        warnings.append("hay efecto de lote: permuta dentro de bloque para no "
                        "confundir lote con señal")
        fam = NullFamily.BLOCK_PERMUTATION
    elif structure.spatial:
        warnings.append("autocorrelación espacial: usa un nulo espacial")
        fam = NullFamily.SPATIAL
    elif structure.phylogenetic:
        warnings.append("estructura filogenética: usa un nulo filogenético")
        fam = NullFamily.PHYLOGENETIC
    elif structure.network:
        warnings.append("estructura de red: usa recableado que preserva el grado")
        fam = NullFamily.NETWORK
    else:
        fam = NullFamily.LABEL_PERMUTATION
    return NullRecommendation(fam, justify(fam), warnings)


def plain_permutation_is_valid(structure: DataStructure) -> bool:
    """A generic label permutation is valid ONLY for i.i.d. data with no structure."""
    return not any((structure.has_groups, structure.temporal, structure.spatial,
                    structure.phylogenetic, structure.network, structure.batch))
