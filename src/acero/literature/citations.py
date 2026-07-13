"""Citation verification and duplicate detection.

Core rule (research_safety: no_fabricated_sources_or_data): a citation is only
valid if it resolves to an ingested document AND, when a fragment is cited, that
fragment actually belongs to that document. Non-existent references are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from .documents import SourceDocument, SourceFragment


@dataclass
class CitationCheck:
    ok: bool
    reason: str


class CitationVerifier:
    def __init__(
        self, documents: list[SourceDocument], fragments: list[SourceFragment]
    ) -> None:
        self._docs = {d.id: d for d in documents}
        self._frags = {f.id: f for f in fragments}

    def verify(self, document_id: str, fragment_id: str | None = None) -> CitationCheck:
        if document_id not in self._docs:
            return CitationCheck(False, f"Document {document_id} does not exist (fabricated citation).")
        if fragment_id is not None:
            frag = self._frags.get(fragment_id)
            if frag is None:
                return CitationCheck(False, f"Fragment {fragment_id} does not exist.")
            if frag.document_id != document_id:
                return CitationCheck(
                    False, f"Fragment {fragment_id} does not belong to document {document_id}."
                )
        return CitationCheck(True, "Citation resolves to real, ingested source.")


def find_duplicate_documents(documents: list[SourceDocument]) -> list[tuple[str, str]]:
    """Return pairs of document ids that share a checksum (exact duplicates)."""
    seen: dict[str, str] = {}
    dups: list[tuple[str, str]] = []
    for d in documents:
        if not d.checksum:
            continue
        if d.checksum in seen:
            dups.append((seen[d.checksum], d.id))
        else:
            seen[d.checksum] = d.id
    return dups
