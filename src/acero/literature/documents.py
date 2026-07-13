"""Document and fragment schemas plus local ingestion.

Ingestion pipeline: document -> checksum -> metadata -> parser -> sections ->
fragments -> (index) -> citations -> provenance. Each fragment keeps enough
location metadata to cite it precisely.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.errors import RetrievalError
from ..core.hashing import hash_file, hash_text
from ..core.ids import new_id

PARSER_VERSION = "text-parser-1"


class SourceDocument(BaseModel):
    id: str
    project_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    source: str = "local"           # local | arxiv | crossref | openalex
    publication_type: str = "unknown"  # preprint | peer_reviewed | book | dataset | unknown
    license: str = "unknown"        # required by data_access policy
    checksum: str = ""
    path: str | None = None
    external_id: str | None = None  # e.g. arXiv id / DOI
    ingested_at: str = Field(default_factory=now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceFragment(BaseModel):
    id: str
    document_id: str
    project_id: str
    section: str = ""
    index: int = 0
    page: int | None = None
    text: str
    char_start: int = 0
    char_end: int = 0
    hash: str = ""
    parser: str = PARSER_VERSION


_SECTION_RE = re.compile(r"^\s*(#+\s+.*|[A-Z][A-Z \-]{3,}|\d+\.\s+.+)$")


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Very small section splitter: detects markdown/allcaps/numbered headings."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = [("body", [])]
    for ln in lines:
        if _SECTION_RE.match(ln) and len(ln.strip()) < 80:
            sections.append((ln.strip().lstrip("# ").strip(), []))
        else:
            sections[-1][1].append(ln)
    return [(name, "\n".join(body).strip()) for name, body in sections if "\n".join(body).strip()]


def chunk_text(
    text: str, *, target_chars: int = 600, overlap: int = 80
) -> list[tuple[int, int, str]]:
    """Split text into overlapping chunks on sentence-ish boundaries.

    Returns list of (char_start, char_end, chunk_text).
    """
    text = text.strip()
    if not text:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + target_chars, n)
        if end < n:
            window = text[start:end]
            brk = max(window.rfind(". "), window.rfind(".\n"), window.rfind("\n\n"))
            if brk > target_chars * 0.4:
                end = start + brk + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((start, end, chunk))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def read_document_text(path: str | Path) -> str:
    """Read text from a .txt/.md file, or a .pdf if a PDF backend is available."""
    p = Path(path)
    if not p.exists():
        raise RetrievalError(f"Document not found: {p}")
    suffix = p.suffix.lower()
    if suffix in {".txt", ".md", ".text"}:
        return p.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        try:  # optional backend; not required for the local-first default
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(p))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pragma: no cover - depends on optional dep
            raise RetrievalError(
                f"PDF backend unavailable for {p.name}: {exc}. "
                "Install 'pypdf' or provide a .txt/.md."
            ) from exc
    raise RetrievalError(f"Unsupported document type: {suffix}")


def ingest_document(
    path: str | Path,
    project_id: str,
    *,
    title: str | None = None,
    authors: list[str] | None = None,
    year: int | None = None,
    license: str = "unknown",
    publication_type: str = "unknown",
    source: str = "local",
    external_id: str | None = None,
) -> tuple[SourceDocument, list[SourceFragment]]:
    """Ingest a local document into a SourceDocument + fragments."""
    p = Path(path)
    text = read_document_text(p)
    checksum = hash_file(p)
    doc = SourceDocument(
        id=new_id("doc"),
        project_id=project_id,
        title=title or p.stem,
        authors=authors or [],
        year=year,
        source=source,
        publication_type=publication_type,
        license=license,
        checksum=checksum,
        path=str(p),
        external_id=external_id,
    )
    fragments: list[SourceFragment] = []
    idx = 0
    for section_name, section_text in _split_sections(text):
        for cstart, cend, chunk in chunk_text(section_text):
            fragments.append(
                SourceFragment(
                    id=new_id("frag"),
                    document_id=doc.id,
                    project_id=project_id,
                    section=section_name,
                    index=idx,
                    text=chunk,
                    char_start=cstart,
                    char_end=cend,
                    hash=hash_text(chunk),
                )
            )
            idx += 1
    if not fragments:
        raise RetrievalError(f"No fragments produced from {p.name} (empty document?)")
    return doc, fragments
