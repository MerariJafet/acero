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
def _isolated_side_effects(tmp_path, monkeypatch):
    """Tests must NEVER touch the user's real data: redirect the DB, the vault,
    the experiment artifacts to per-test temp paths, and silence the async
    subagents. Fixes integration tests (create_app) polluting the real DB with
    'Disc API'/'API project' projects on every `make verify`."""
    monkeypatch.setenv("ACERO_DB_URL", f"sqlite:///{tmp_path / 'acero_test.sqlite'}")
    monkeypatch.setenv("ACERO_OBSIDIAN_VAULT", str(tmp_path / "_test_vault"))
    monkeypatch.setenv("ACERO_CRITIC_DISABLED", "1")
    monkeypatch.setenv("ACERO_EXPERIMENT_ARTIFACTS", str(tmp_path / "_test_artifacts"))
    monkeypatch.setenv("ACERO_MISSIONS_DISABLED", "1")
    monkeypatch.setenv("ACERO_WATCHDOG_DISABLED", "1")
    monkeypatch.setenv("ACERO_EMBEDDINGS_DISABLED", "1")  # no heavy model in tests
    # el cortacircuitos de credenciales vive en $HOME: si la sesión real del
    # humano está caída, la suite empezaba a fallar sola (visto el 2026-08-21).
    # Un test jamás debe depender de si alguien está logueado.
    monkeypatch.setenv("ACERO_AGENT_BREAKER", str(tmp_path / "_agent_breaker.json"))
    # mismo principio para el token del CLI: la guardia anti-carrera de refresco
    # lee ~/.claude/.credentials.json; la suite no debe ni mirar ese archivo ni
    # depender de cuánta vida le quede al token real del humano.
    monkeypatch.setenv("ACERO_CLAUDE_CREDS", str(tmp_path / "_claude_creds.json"))
    # get_config() is lru_cached — force it to re-read the temp DB_URL each test
    from acero.core.config import get_config
    get_config.cache_clear()
    yield
    get_config.cache_clear()


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
