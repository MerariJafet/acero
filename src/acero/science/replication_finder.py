"""Replication-source finder — data with an INDEPENDENT provenance root, on demand.

The bottleneck for genuine external replication is NOT data volume or storage — ACERO
fetches on demand, keeps hashes, prunes bulk and indexes lightly. The bottleneck is
finding, for a SPECIFIC claim, a dataset that (a) measures the same phenomenon and (b)
comes from a DIFFERENT curation root than the original (so the IndependenceGraph doesn't
degrade it to SAME_STUDY).

This module answers "give me the same phenomenon, but NOT from <root>". It combines a
curated map of which repositories carry which phenomena (each with its provenance root)
with a live generalist search (Zenodo), assigns provenance roots, and certifies each
candidate against the target via the IndependenceGraph. Sources it cannot auto-resolve are
returned as honest SEARCH DIRECTIVES, never fabricated URLs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .independence_graph import (
    DatasetProvenance,
    IndependenceGraph,
    IndependenceKind,
)

# curation ecosystem → provenance root. Two datasets sharing a root are NOT independent.
REPO_ROOTS: dict[str, str] = {
    "TDC": "TDC/HarvardDataverse",
    "ChEMBL": "ChEMBL/EBI",
    "PubChem": "PubChem/NCBI",
    "GEO": "GEO/NCBI",
    "NASA-NEA": "NASA/IPAC",
    "GWOSC": "GWOSC/LIGO",
    "SILSO": "SILSO",
    "Figshare": "Figshare",     # each article is a distinct upload (see root_for)
    "Dryad": "Dryad",
    "Zenodo": "Zenodo",
    "literature": "primary-literature",
}


def root_for(repository: str, accession: str = "") -> str:
    """Provenance root for a source. Generalist repos (Zenodo/Figshare/Dryad) mint a
    per-record root because each deposit is an independent curation act."""
    base = REPO_ROOTS.get(repository, repository or "unknown")
    if repository in ("Zenodo", "Figshare", "Dryad") and accession:
        return f"{base}:{accession}"
    return base


@dataclass
class SourceHint:
    """A place the same phenomenon can be found, with how to get it."""
    repository: str
    fetch_kind: str            # "resolver" (auto-fetchable) | "directive" (manual search)
    reference: str             # accession/query/directive text
    note: str = ""


# phenomenon keyword → independent-source hints (roots other than the usual one)
_SOURCE_KB: list[tuple[str, list[SourceHint]]] = [
    ("caco2|permeab|pampa", [
        SourceHint("ChEMBL", "directive",
                   "buscar ensayos de permeabilidad (Caco-2/PAMPA) en ChEMBL por "
                   "assay_chembl_id; raíz de curación distinta a TDC"),
        SourceHint("Zenodo", "resolver", "caco2 permeability dataset",
                   "búsqueda viva en Zenodo (cada depósito, raíz independiente)"),
        SourceHint("literature", "directive",
                   "dataset primario de permeabilidad de un paper (SI/tabla)"),
    ]),
    ("solubil", [
        SourceHint("Zenodo", "resolver", "aqueous solubility dataset"),
        SourceHint("ChEMBL", "directive", "ensayos de solubilidad en ChEMBL"),
    ]),
    ("methylat|metilaci|ewas|cpg", [
        SourceHint("GEO", "directive",
                   "otra serie GEO del mismo fenotipo, otro estudio/cohorte"),
        SourceHint("Zenodo", "resolver", "methylation EWAS replication dataset"),
    ]),
    ("exoplanet|radius valley|valle de radios", [
        SourceHint("Zenodo", "resolver", "exoplanet radius catalog"),
        SourceHint("literature", "directive",
                   "otro release/survey (TESS, K2) con radios independientes"),
    ]),
]


@dataclass
class ReplicationCandidate:
    repository: str
    provenance_root: str
    fetch_kind: str
    reference: str
    independence_kind: IndependenceKind
    replication_capable: bool
    note: str = ""

    def summary(self) -> dict[str, object]:
        return {"repository": self.repository, "root": self.provenance_root,
                "fetch_kind": self.fetch_kind, "reference": self.reference,
                "independence": self.independence_kind.name,
                "replication_capable": self.replication_capable, "note": self.note}


def _hints_for(phenomenon: str) -> list[SourceHint]:
    import re
    p = (phenomenon or "").lower()
    out: list[SourceHint] = []
    for pattern, hints in _SOURCE_KB:
        if re.search(pattern, p):
            out.extend(hints)
    return out


def zenodo_search(query: str, *, size: int = 5, opener: Any | None = None
                  ) -> list[SourceHint]:
    """Live generalist search: Zenodo datasets for a phenomenon. Each record is an
    independent curation root, so a match is a candidate independent source."""
    import urllib.parse

    from ._http import get_json
    url = ("https://zenodo.org/api/records?" +
           urllib.parse.urlencode({"q": query, "size": size, "type": "dataset"}))
    try:
        data = get_json(url, opener)
    except Exception:  # noqa: BLE001 - search is best-effort
        return []
    hits = (((data or {}).get("hits") or {}).get("hits")) or []
    out: list[SourceHint] = []
    for h in hits[:size]:
        rec_id = str(h.get("id", ""))
        title = ((h.get("metadata") or {}).get("title") or "")[:80]
        if rec_id:
            out.append(SourceHint("Zenodo", "resolver", f"zenodo:{rec_id}",
                                  f"Zenodo {rec_id}: {title}"))
    return out


def find_replication_sources(
        phenomenon: str, target_provenance: DatasetProvenance,
        *, live_search: bool = False, opener: Any | None = None
        ) -> list[ReplicationCandidate]:
    """Return candidate sources for the SAME phenomenon from a DIFFERENT provenance root
    than `target_provenance`, each certified by the IndependenceGraph."""
    hints = _hints_for(phenomenon)
    if live_search:
        for h in _hints_for(phenomenon):
            if h.repository == "Zenodo":
                hints += zenodo_search(h.reference, opener=opener)
                break

    graph = IndependenceGraph()
    graph.add(target_provenance)
    candidates: list[ReplicationCandidate] = []
    seen: set[str] = set()
    for h in hints:
        acc = h.reference.split(":", 1)[1] if h.reference.startswith(
            ("zenodo:", "figshare:", "dryad:")) else ""
        root = root_for(h.repository, acc)
        key = (h.repository, root, h.reference)
        if key in seen:
            continue
        seen.add(str(key))
        cand_id = f"cand::{h.repository}::{root}"
        graph.add(DatasetProvenance(cand_id, provenance_root=root,
                                    repository=h.repository, assay_source=h.reference))
        v = graph.independence(target_provenance.dataset_id, cand_id)
        candidates.append(ReplicationCandidate(
            h.repository, root, h.fetch_kind, h.reference, v.kind,
            v.is_replication_capable, h.note))
    # replication-capable + auto-fetchable first
    candidates.sort(key=lambda c: (not c.replication_capable, c.fetch_kind != "resolver"))
    return candidates
