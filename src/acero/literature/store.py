"""Persistence for documents and fragments, plus index (re)construction."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..ledger.models import DocumentRow, FragmentRow
from .documents import SourceDocument, SourceFragment
from .retrieval import BM25Index


class LiteratureStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add(self, doc: SourceDocument, fragments: list[SourceFragment]) -> None:
        with self._sf() as s:
            s.add(DocumentRow(
                id=doc.id, project_id=doc.project_id,
                checksum=doc.checksum, payload=doc.model_dump(),
            ))
            for f in fragments:
                s.add(FragmentRow(
                    id=f.id, document_id=f.document_id,
                    project_id=f.project_id, payload=f.model_dump(),
                ))
            s.commit()

    def documents(self, project_id: str) -> list[SourceDocument]:
        with self._sf() as s:
            rows = s.execute(
                select(DocumentRow).where(DocumentRow.project_id == project_id)
            ).scalars().all()
            return [SourceDocument(**r.payload) for r in rows]

    def fragments(self, project_id: str) -> list[SourceFragment]:
        with self._sf() as s:
            rows = s.execute(
                select(FragmentRow).where(FragmentRow.project_id == project_id)
            ).scalars().all()
            return [SourceFragment(**r.payload) for r in rows]

    def build_index(self, project_id: str) -> BM25Index:
        idx = BM25Index()
        idx.add_many(self.fragments(project_id))
        return idx
