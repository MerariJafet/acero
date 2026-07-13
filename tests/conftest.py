"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.ledger.service import ResearchLedger
from acero.literature.store import LiteratureStore

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture()
def ledger(session_factory) -> ResearchLedger:
    return ResearchLedger(session_factory)


@pytest.fixture()
def lit_store(session_factory) -> LiteratureStore:
    return LiteratureStore(session_factory)


@pytest.fixture()
def project(ledger):
    return ledger.create_project("Test project", description="unit tests", domain="physics")


@pytest.fixture()
def corpus_dir() -> Path:
    return FIXTURE_CORPUS
