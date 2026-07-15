"""Sprint 11 tests: async-safe gate context, action scoping, UoW rollback."""

from __future__ import annotations

import asyncio
import threading

import pytest
from sqlalchemy import create_engine

from acero.epistemic_gate.exceptions import BypassDetected
from acero.epistemic_gate.transaction import (
    current,
    enforcement_enabled,
    gate_context,
    in_context,
    require_context,
)
from acero.epistemic_gate.unit_of_work import UnitOfWork, UoWState
from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.ledger.service import ResearchLedger
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType


def _wm():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    led = ResearchLedger(sf)
    proj = led.create_project("t", domain="physics")
    return WorldModel(sf, led, project_id=proj.id)


def test_context_propagates_into_async_task():
    async def run():
        with enforcement_enabled(), gate_context("world_model.link", "WORLD_MODEL_UPDATE",
                                                 "tok", allowed_mutations=("world_model.link",)):
            async def child():
                # contextvars propagate into the task's copied context
                require_context("world_model.link", action="world_model.link")
                return current().action

            return await asyncio.create_task(child())

    assert asyncio.run(run()) == "world_model.link"


def test_context_scoped_to_its_action():
    with enforcement_enabled(), gate_context("world_model.update_belief",
                                             "WORLD_MODEL_UPDATE", "tok",
                                             allowed_mutations=("world_model.update_belief",)):
        require_context("world_model.update_belief", action="world_model.update_belief")
        with pytest.raises(BypassDetected):
            require_context("world_model.link", action="world_model.link")


def test_no_context_raises_when_enforced():
    with enforcement_enabled():
        with pytest.raises(BypassDetected):
            require_context("world_model.update_belief")
    assert not in_context()


def test_concurrent_threads_without_context_all_blocked():
    wm = _wm()
    n = wm.create(NodeType.HYPOTHESIS, "h")
    blocked = []
    lock = threading.Lock()

    def attempt():
        with enforcement_enabled():
            try:
                wm.update_belief(n.id, event="sneak", evidence=0.5)
            except BypassDetected:
                with lock:
                    blocked.append(1)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(blocked) == 8


def test_thread_does_not_inherit_parent_context():
    """A worker thread starts with a fresh (empty) contextvars copy — no leaked auth."""
    seen = {}

    def worker():
        seen["in_context"] = in_context()

    with enforcement_enabled(), gate_context("a", "S", "tok"):
        t = threading.Thread(target=worker)
        t.start()
        t.join()
    assert seen["in_context"] is False        # thread did not inherit the open context


def test_unit_of_work_commits_all_steps():
    uow = UnitOfWork("multi")
    state = {"ledger": 0, "world": 0}
    uow.add("ledger", lambda: state.__setitem__("ledger", 1))
    uow.add("world", lambda: state.__setitem__("world", 1))
    uow.commit()
    assert uow.state == UoWState.COMMITTED
    assert state == {"ledger": 1, "world": 1}


def test_unit_of_work_rolls_back_on_failure():
    uow = UnitOfWork("multi")
    state = {"a": 0, "b": 0}
    uow.add("a", lambda: state.__setitem__("a", 1), lambda: state.__setitem__("a", 0))
    uow.add("b", lambda: state.__setitem__("b", 1), lambda: state.__setitem__("b", 0))
    uow.add("boom", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(RuntimeError):
        uow.commit()
    assert uow.state == UoWState.FAILED
    assert state == {"a": 0, "b": 0}          # both prior steps rolled back
    assert any("undo:" in e for e in uow.attempt_log)   # attempt preserved in log
