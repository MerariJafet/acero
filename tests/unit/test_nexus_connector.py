"""NEXUS connector — normalize NEXUS payloads; API→snapshot→empty fallback (offline)."""
from __future__ import annotations

import json

import pytest

from acero.integrations.nexus import NexusConnector, normalize


@pytest.fixture(autouse=True)
def _root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_ECON_ROOT", str(tmp_path / "econ"))


def test_normalize_maps_common_fields():
    raw = {"income": 50000, "expenses": 32000, "currency": "MXN",
           "expenses_by_category": {"renta": 12000, "comida": 8000},
           "accounts": [{"name": "BBVA", "balance": 15000}]}
    s = normalize(raw, source="test")
    assert s["available"] and s["income"] == 50000 and s["net"] == 18000
    cats = {c["category"]: c["amount"] for c in s["expenses_by_category"]}
    assert cats["renta"] == 12000 and cats["comida"] == 8000
    assert s["accounts"][0] == {"name": "BBVA", "balance": 15000.0}


def test_api_first_success():
    def http(method, url, headers):
        assert method == "GET" and url.endswith("/summary")
        return {"income": 10, "expenses": 4}
    s = NexusConnector(http=http).fetch_snapshot()
    assert s["available"] and s["source"] == "nexus-api/summary" and s["net"] == 6


def test_falls_back_to_snapshot_file(tmp_path, monkeypatch):
    from acero.integrations import nexus
    monkeypatch.setattr(nexus, "snapshot_path",
                        lambda: tmp_path / "econ" / "nexus_snapshot.json")
    p = tmp_path / "econ" / "nexus_snapshot.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"income": 7, "expenses": 2}), encoding="utf-8")

    def http(method, url, headers):
        raise RuntimeError("nexus down")
    s = NexusConnector(http=http).fetch_snapshot()
    assert s["available"] and s["source"] == "snapshot-file" and s["net"] == 5


def test_empty_when_nothing_available_never_fabricates():
    def http(method, url, headers):
        raise RuntimeError("down")
    s = NexusConnector(http=http).fetch_snapshot()
    assert s["available"] is False
    assert s["income"] is None and s["expenses_by_category"] == []
    assert "NEXUS no disponible" in s["reason"]
