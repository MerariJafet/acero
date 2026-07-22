"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from acero.discovery.store import DiscoveryStore
from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.ledger.service import ResearchLedger
from acero.literature.store import LiteratureStore

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@pytest.fixture(autouse=True)
def _isolated_obsidian_vault(tmp_path, monkeypatch):
    """Tests must NEVER write to the user's real ACERO-Research vault, and the
    async critic subagent must never fire real Codex processes from tests."""
    monkeypatch.setenv("ACERO_OBSIDIAN_VAULT", str(tmp_path / "_test_vault"))
    monkeypatch.setenv("ACERO_CRITIC_DISABLED", "1")


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


@pytest.fixture()
def disc_store(session_factory, ledger) -> DiscoveryStore:
    return DiscoveryStore(session_factory, ledger)


@pytest.fixture()
def mock_candidates(project):
    """A diverse set of 8 mock hypothesis candidates for a project."""
    from acero.discovery.generation import MockHypothesisGenerator

    return MockHypothesisGenerator().generate(
        "What model explains the data?", project_id=project.id,
        research_question_id="q_test", context={"variables": ["t", "y"]}, n=8)
