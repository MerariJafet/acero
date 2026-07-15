"""Sprint 13 tests: lightweight schema versioning."""

from __future__ import annotations

from sqlalchemy import create_engine

from acero.core.schema_version import (
    CURRENT_SCHEMA_VERSION,
    check,
    current_db_version,
    ensure_stamped,
    stamp,
)
from acero.ledger.db import make_session_factory
from acero.ledger.models import Base


def _sf():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    return make_session_factory(eng)


def test_fresh_db_has_no_version_then_stamps():
    sf = _sf()
    assert current_db_version(sf) is None
    ensure_stamped(sf)
    assert current_db_version(sf) == CURRENT_SCHEMA_VERSION


def test_check_reports_up_to_date_after_stamp():
    sf = _sf()
    ensure_stamped(sf)
    st = check(sf)
    assert st.compatible and st.db_version == CURRENT_SCHEMA_VERSION


def test_legacy_db_is_compatible_but_unstamped():
    sf = _sf()
    st = check(sf)                              # no rows yet
    assert st.compatible and st.db_version is None


def test_newer_db_is_incompatible():
    sf = _sf()
    stamp(sf, version=CURRENT_SCHEMA_VERSION + 5, note="future")
    st = check(sf)
    assert not st.compatible and "NEWER" in st.detail


def test_stamp_is_idempotent():
    sf = _sf()
    stamp(sf)
    stamp(sf)
    with sf() as s:
        from acero.ledger.models import SchemaVersionRow
        rows = s.query(SchemaVersionRow).filter_by(version=CURRENT_SCHEMA_VERSION).all()
    assert len(rows) == 1
