"""Sprint 23: the World Model Explorer must scale — paginate, never load the full graph.

Seeds 10,000 synthetic nodes and asserts a single page query returns a bounded slice
plus an accurate total, quickly, without materialising every node.
"""

from __future__ import annotations

import time

from sqlalchemy import create_engine

from acero.ledger.db import make_session_factory
from acero.ledger.models import Base, WorldNodeRow
from acero.ledger.service import ResearchLedger
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType


def _seed(n: int = 10_000):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    with sf() as s:
        for i in range(n):
            s.add(WorldNodeRow(
                id=f"wn_{i:06d}", project_id="big", program_id=None,
                type=NodeType.CLAIM.value, label=f"claim number {i}",
                confidence=(i % 100) / 100.0, version=1,
                payload={"id": f"wn_{i:06d}", "type": NodeType.CLAIM.value,
                         "label": f"claim number {i}", "confidence": (i % 100) / 100.0,
                         "version": 1}))
        s.commit()
    return WorldModel(sf, ResearchLedger(sf), "big")


def test_page_query_is_bounded_and_fast():
    wm = _seed(10_000)
    t0 = time.perf_counter()
    page = wm.page_nodes(offset=0, limit=50)
    elapsed = time.perf_counter() - t0
    assert page["total"] == 10_000
    assert page["returned"] == 50            # only one page materialised
    assert len(page["items"]) == 50
    assert page["has_more"] is True
    assert elapsed < 1.0                     # SQL LIMIT, not a full scan in Python


def test_pagination_walks_without_overlap():
    wm = _seed(1_000)
    seen = set()
    offset = 0
    while True:
        page = wm.page_nodes(offset=offset, limit=100)
        for item in page["items"]:
            assert item["id"] not in seen    # no duplicates across pages
            seen.add(item["id"])
        if not page["has_more"]:
            break
        offset += 100
    assert len(seen) == 1_000


def test_search_filter_at_sql_level():
    wm = _seed(1_000)
    page = wm.page_nodes(search="number 42", limit=200)
    # "number 42", "number 420".."429" -> 11 matches, all contain the substring
    assert page["total"] == 11
    assert all("number 42" in i["label"] for i in page["items"])


def test_limit_capped():
    wm = _seed(500)
    page = wm.page_nodes(offset=0, limit=99999)
    assert page["returned"] <= 200           # hard cap protects the server
