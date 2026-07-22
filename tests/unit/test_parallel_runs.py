"""Parallel runs: one subagent per hypothesis/experiment, live progress (offline)."""

from __future__ import annotations

import time

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.parallel_runs import (
    get_run,
    start_investigate_all,
    start_run,
    start_run_all_experiments,
)


@pytest.fixture()
def file_session_factory(tmp_path):
    """Threads need a FILE-based sqlite (a :memory: db is per-connection, so each
    subagent thread would see an empty database). Mirrors production WAL setup."""
    from sqlalchemy import create_engine, event

    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    engine = create_engine(f"sqlite:///{tmp_path / 'par.db'}", future=True,
                           connect_args={"timeout": 30})

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def _wait_done(run_id: str, timeout: float = 30.0) -> dict:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        r = get_run(run_id)
        if r and r["status"] == "DONE":
            return r
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s")


def test_start_run_parallel_and_progress():
    seen: list[str] = []

    def work(item):
        time.sleep(0.05)
        seen.append(item["id"])
        return {"summary": f"ok {item['id']}"}

    run = start_run("demo", [{"id": f"i{k}", "label": f"item {k}"} for k in range(5)],
                    work, max_workers=3)
    assert run["status"] == "RUNNING" and run["total"] == 5
    done = _wait_done(run["id"])
    assert done["done"] == 5
    assert sorted(seen) == [f"i{k}" for k in range(5)]
    assert all(i["status"] == "DONE" for i in done["items"])


def test_start_run_isolates_failures():
    def work(item):
        if item["id"] == "bad":
            raise RuntimeError("boom")
        return {"summary": "ok"}

    run = start_run("demo", [{"id": "bad", "label": "b"}, {"id": "good", "label": "g"}],
                    work)
    done = _wait_done(run["id"])
    by_id = {i["id"]: i for i in done["items"]}
    assert by_id["bad"]["status"] == "ERROR" and "boom" in by_id["bad"]["summary"]
    assert by_id["good"]["status"] == "DONE"     # one failed subagent doesn't kill the run


def test_empty_run_finishes_immediately():
    run = start_run("demo", [], lambda i: {})
    assert run["status"] == "DONE" and run["total"] == 0


def test_investigate_all_parallel_offline(file_session_factory):
    lg = ResearchLedger(file_session_factory)
    p = lg.create_project("Par", domain="astronomy")
    hs = HypothesisService(file_session_factory)
    fl = HypothesisFlow(file_session_factory)
    created = hs.generate(p.id, use_ai=False)["created"]
    for h in created[:2]:
        fl.set_status(p.id, h["id"], "APPROVED", "x")
    run = start_investigate_all(p.id, use_ai=False, session_factory=file_session_factory)
    done = _wait_done(run["id"])
    assert done["total"] == 2
    # each subagent persisted its literature run
    for h in created[:2]:
        cur = fl.store.get(h["id"])
        assert cur["lit_status"] == "DONE"


def test_run_all_experiments_parallel_offline(file_session_factory):
    lg = ResearchLedger(file_session_factory)
    p = lg.create_project("ParExp", domain="astronomy")
    h = HypothesisService(file_session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(file_session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    fl.propose_experiments(p.id, h["id"], use_ai=False)
    run = start_run_all_experiments(p.id, use_ai=False, session_factory=file_session_factory)
    done = _wait_done(run["id"])
    assert done["total"] >= 1
    assert all(i["status"] == "DONE" for i in done["items"])
    sts = {e.get("status") for e in fl.store.list_objects(p.id, kind="experiment")}
    assert sts <= {"PLANNED", "COMPLETE"}          # nothing left PROPOSED
