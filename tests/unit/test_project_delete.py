"""delete_project: hard cascade delete of a project and all its data (offline)."""
from __future__ import annotations

import pytest

from acero.core.errors import IntegrityError
from acero.discovery.store import DiscoveryStore
from acero.ledger.service import ResearchLedger


def _seed(session_factory):
    lg = ResearchLedger(session_factory)
    store = DiscoveryStore(session_factory, lg)
    p = lg.create_project("Borrar", domain="astronomy")
    store.put(p.id, "candidate", "hyp_del1", {"id": "hyp_del1", "title": "h"},
              status="APPROVED")
    store.put(p.id, "experiment", "exp_del1", {"id": "exp_del1", "title": "e"},
              status="DONE")
    return lg, store, p


def test_delete_project_cascades(session_factory):
    lg, store, p = _seed(session_factory)
    assert lg.get_project(p.id) is not None
    assert len(store.list_objects(p.id)) == 2

    out = lg.delete_project(p.id)
    assert out["ok"] is True and out["deleted_rows"] >= 2

    assert lg.get_project(p.id) is None            # project gone
    assert store.list_objects(p.id) == []          # discovery objects gone


def test_delete_missing_project_raises(session_factory):
    lg = ResearchLedger(session_factory)
    with pytest.raises(IntegrityError):
        lg.delete_project("proj_does_not_exist")


def test_delete_one_project_leaves_others_intact(session_factory):
    lg, store, p = _seed(session_factory)
    other = lg.create_project("Queda", domain="genetics")
    store.put(other.id, "candidate", "hyp_keep", {"id": "hyp_keep"}, status="PROPOSED")

    lg.delete_project(p.id)

    assert lg.get_project(other.id) is not None
    assert len(store.list_objects(other.id)) == 1  # untouched
