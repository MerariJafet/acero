"""Experiment detail dashboard payload (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.lifecycle import Lifecycle


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Det", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]
    return p, h, e, fl


def test_detail_missing(session_factory):
    assert Lifecycle(session_factory).experiment_detail("x", "nope")["ok"] is False


def test_detail_of_completed_experiment(session_factory, tmp_path):
    p, h, e, fl = _setup(session_factory)
    adir = tmp_path / "exp_art"
    (adir).mkdir()
    (adir / "script.py").write_text("print('RESULT_JSON: {}')", encoding="utf-8")
    (adir / "stdout.txt").write_text("corriendo…\nRESULT_JSON: {...}", encoding="utf-8")
    (adir / "out").mkdir()
    (adir / "out" / "fig1.png").write_bytes(b"\x89PNG")
    fl.store.update_payload(e["id"], {
        "status": "COMPLETE", "artifacts_dir": str(adir),
        "provenance": [{"url": "https://sidc.be/x.csv", "filename": "x.csv",
                        "bytes": 2048, "sha256": "ab" * 32, "pruned": True}],
        "factory": {"attempts": 1, "duration_sec": 3.2},
        "result": {"metrics": {"snr": 4.1, "n": 500},
                   "verdict": "refutes", "verdict_reason": "ruido",
                   "null_test": {"description": "surrogatos", "statistic": 4.1,
                                 "threshold": 3.0, "passed": True},
                   "anomalies": ["outlier en 1998"]}})
    out = Lifecycle(session_factory).experiment_detail(p.id, e["id"])
    assert out["ok"] is True
    d = out["experiment"]
    assert d["verdict"] == "refutes" and d["metrics"]["snr"] == 4.1
    assert d["null_test"]["passed"] is True
    assert d["figures"] == ["fig1.png"]
    assert d["provenance"][0]["pruned"] is True
    assert "RESULT_JSON" in d["code"] and "corriendo" in d["stdout"]
    assert d["anomalies"] == ["outlier en 1998"]
    assert d["hyp_tag"] == h["tag"]


def test_detail_without_artifacts_is_still_ok(session_factory):
    p, h, e, fl = _setup(session_factory)
    fl.store.update_payload(e["id"], {"status": "PLANNED",
                                      "plan": "bajar datos y ajustar"})
    d = Lifecycle(session_factory).experiment_detail(p.id, e["id"])["experiment"]
    assert d["status"] == "PLANNED" and d["plan"].startswith("bajar")
    assert d["code"] == "" and d["figures"] == []


def test_sin_artifacts_dir_no_lee_el_cwd(session_factory, tmp_path, monkeypatch):
    """Path("") es PosixPath(".") — truthy Y existente. Un experimento sin
    artifacts_dir leía ./script.py, ./stdout.txt y ./out/*.png del directorio donde
    corría el portal y los servía como si fueran del experimento (en el repo había un
    script.py de 18KB que se colaba en el dashboard de cualquier PLANNED)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "script.py").write_text("SECRETO_DEL_CWD = 1", encoding="utf-8")
    (tmp_path / "stdout.txt").write_text("salida ajena", encoding="utf-8")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "ajena.png").write_bytes(b"\x89PNG")

    p, h, e, fl = _setup(session_factory)
    fl.store.update_payload(e["id"], {"status": "PLANNED", "artifacts_dir": ""})
    d = Lifecycle(session_factory).experiment_detail(p.id, e["id"])["experiment"]
    assert d["code"] == "" and d["stdout"] == "" and d["figures"] == []


def test_artifacts_dir_apuntando_a_un_archivo_no_revienta(session_factory, tmp_path):
    """Defensa del guard: si artifacts_dir apunta a algo que no es directorio,
    se ignora en vez de lanzar."""
    p, h, e, fl = _setup(session_factory)
    f = tmp_path / "no_soy_dir.txt"
    f.write_text("x", encoding="utf-8")
    fl.store.update_payload(e["id"], {"status": "PLANNED", "artifacts_dir": str(f)})
    d = Lifecycle(session_factory).experiment_detail(p.id, e["id"])["experiment"]
    assert d["code"] == "" and d["figures"] == []
