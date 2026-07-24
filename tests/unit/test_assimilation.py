"""E1-E3: null-byte fix, Zenodo resolver, playbook injection, autonomous rigor loop."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal import data_resolver as dr
from acero.portal import experiment_factory as fx
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import STEPS, MissionEngine
from acero.portal.playbook import brief, playbook


def test_sanitize_strips_null_and_control_bytes():
    assert fx._sanitize("a\x00b\x07c") == "abc"
    assert fx._sanitize("linea1\nlinea2\tcol") == "linea1\nlinea2\tcol"  # keep \n \t


def test_head_preview_survives_binary(tmp_path):
    p = tmp_path / "bin.csv"
    p.write_bytes(b"col_a,col_b\n1\x00,2\x00\n\x07\x08binary")
    prev = fx._head_preview(p)
    assert "\x00" not in prev and "col_a" in prev


def test_playbook_loaded_and_has_discovery_sources():
    txt = playbook()
    assert "DESCUBRIR" in txt and "Cruce de datos" in txt and "control NULO" in txt
    assert len(brief(500)) == 500


def test_zenodo_resolver_lists_data_files(monkeypatch):
    import json as _j

    class Resp:
        def read(self):
            return _j.dumps({"files": [
                {"key": "surface_code_data.csv",
                 "links": {"self": "https://zenodo.org/api/records/123/files/surface_code_data.csv/content"},
                 "size": 1000},
                {"key": "README.pdf", "links": {"self": "https://x/readme.pdf"}}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    specs = dr.zenodo_files("123", opener=lambda req, timeout=0: Resp())
    names = [s["filename"] for s in specs]
    assert "surface_code_data.csv" in names and "README.pdf" not in names
    assert specs[0]["repository"] == "Zenodo"


def test_resolve_reference_finds_zenodo_doi(monkeypatch):
    import json as _j

    class Resp:
        def read(self):
            return _j.dumps({"files": [
                {"key": "qec.csv", "links": {"self": "https://zenodo.org/x/qec.csv"},
                 "size": 10}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(dr.urllib.request, "urlopen",
                        lambda req, timeout=0: Resp())
    specs = dr.resolve_reference("datos en 10.5281/zenodo.7057665 de códigos de superficie")
    assert specs and specs[0]["repository"] == "Zenodo"


def test_mission_has_rigor_loop_step(session_factory):
    assert STEPS[-1] == "rigor_loop"
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Rig", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)   # offline
    m = eng.store.get(r["mission_id"])
    assert m["status"] == "DONE"
    rl = next(s for s in m["steps"] if s["name"] == "rigor_loop")
    assert rl["status"] == "DONE" and "omitido" in rl["info"]  # offline → skipped
