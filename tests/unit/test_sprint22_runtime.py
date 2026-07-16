"""Sprint 22 tests: Alembic migrations, config profiles, atomic claim, observability."""

from __future__ import annotations

import tempfile

import pytest
from sqlalchemy import create_engine, inspect

from acero.migrations import api
from acero.runtime.profiles import (
    PROFILES,
    UnsafeProfileStartError,
    check_startup,
    get_profile,
)

# --- Alembic migrations ---------------------------------------------------

def _tmp_url():
    return f"sqlite:///{tempfile.mkdtemp()}/m.sqlite"


def test_migration_upgrade_creates_full_schema():
    url = _tmp_url()
    assert api.current(url) is None
    assert api.upgrade(url) == "0001_baseline"
    tabs = inspect(create_engine(url)).get_table_names()
    for required in ("projects", "runtime_tasks", "world_nodes", "discovery",
                     "schema_version", "alembic_version"):
        assert required in tabs


def test_migration_downgrade_drops_schema():
    url = _tmp_url()
    api.upgrade(url)
    api.downgrade(url)
    tabs = [t for t in inspect(create_engine(url)).get_table_names() if t != "alembic_version"]
    assert tabs == []


def test_migration_check_reports_status():
    url = _tmp_url()
    assert api.check(url)["status"].startswith("unmanaged")
    api.upgrade(url)
    c = api.check(url)
    assert c["at_head"] and c["status"] == "up_to_date"


def test_migration_upgrade_is_idempotent_on_create_all_db():
    """An RC1/RC2 DB built via create_all can be stamped/upgraded without duplication."""
    from acero.ledger.models import Base
    url = _tmp_url()
    Base.metadata.create_all(create_engine(url))       # pre-existing create_all schema
    api.upgrade(url)                                    # checkfirst=True → no error
    assert api.check(url)["at_head"]


def test_migration_history_lists_baseline():
    assert any(h["revision"] == "0001_baseline" for h in api.history(_tmp_url()))


# --- config profiles ------------------------------------------------------

def test_all_profiles_present():
    assert set(PROFILES) == {"development", "research", "review", "production-local", "test"}


def test_production_local_refuses_dev_secret():
    with pytest.raises(UnsafeProfileStartError):
        check_startup("production-local", secret_configured=False)
    check_startup("production-local", secret_configured=True)   # ok with a real secret


def test_development_profile_starts_without_secret():
    check_startup("development", secret_configured=False)        # no raise


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        get_profile("nope")


# --- atomic claim (multiprocess double-claim regression) ------------------

def test_atomic_claim_no_double_claim(tmp_path):
    """Regression for the burn-in finding: two claims never return the same task."""
    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    from acero.runtime.queue import ResearchQueue
    eng = create_engine(f"sqlite:///{tmp_path}/q.sqlite", future=True)
    Base.metadata.create_all(eng)
    q = ResearchQueue(make_session_factory(eng))
    for i in range(5):
        q.enqueue(f"t{i}", "k")
    claimed = [q.claim(f"w{i}") for i in range(5)]
    ids = [c["id"] for c in claimed if c]
    assert len(ids) == len(set(ids)) == 5              # each task claimed exactly once


def test_multiprocess_burnin_no_duplication(tmp_path):
    from acero.benchmarks.runtime_burnin import run_burnin
    r = run_burnin(str(tmp_path / "burn"))
    assert r["all_passed"], [k for k, c in r["cases"].items() if not c["passed"]]
    assert r["cases"]["multiprocess_no_duplication"]["no_duplication"]


# --- observability --------------------------------------------------------

def test_metrics_snapshot_and_prometheus(tmp_path):
    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    from acero.runtime.observability import metrics_snapshot, prometheus_text
    from acero.runtime.queue import ResearchQueue
    eng = create_engine(f"sqlite:///{tmp_path}/o.sqlite", future=True)
    Base.metadata.create_all(eng)
    q = ResearchQueue(make_session_factory(eng))
    q.enqueue("a", "k")
    m = metrics_snapshot(q.store)
    assert m["tasks_total"] == 1 and m["queued"] == 1
    assert "acero_tasks_total 1" in prometheus_text(q.store)


# --- runtime security -----------------------------------------------------

def test_forged_token_rejected():
    from acero.epistemic_gate.tokens import TokenError, TokenRegistry
    reg = TokenRegistry(ttl_seconds=30)
    tok = reg.issue(action="a", project_id="p")
    tok.signature = "0" * 64                            # forged
    with pytest.raises(TokenError):
        reg.validate(tok, action="a", project_id="p")


def test_expired_lease_task_reclaimed_not_lost(tmp_path):
    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    from acero.runtime.queue import ResearchQueue
    eng = create_engine(f"sqlite:///{tmp_path}/e.sqlite", future=True)
    Base.metadata.create_all(eng)
    q = ResearchQueue(make_session_factory(eng), lease_seconds=0)
    q.enqueue("j", "k")
    q.claim("dead")
    assert q.reap_expired() == ["j"]                    # not lost
    assert q.claim("alive") is not None                 # reclaimable


def test_metrics_endpoint_local_only():
    from fastapi.testclient import TestClient

    from acero.api.app import create_app
    r = TestClient(create_app()).get("/portal/api/metrics")
    assert r.status_code == 200 and "acero_tasks_total" in r.text
