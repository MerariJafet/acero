"""Experiment Factory: codegen→sandbox→validated result (offline, injected steps)."""

from __future__ import annotations

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal.experiment_factory import (
    _host_allowed,
    _parse_result,
    fetch_data,
    run_generated,
)
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow

EXP = {"id": "exp_t1", "title": "prueba nula", "what": "w", "how": "h",
       "data_source": "sintético", "controls": "shuffle",
       "discriminator": "snr>3", "method_type": "simulation"}
HYP = {"title": "hipótesis de prueba"}

GOOD_SCRIPT = """
import json
import numpy as np
rng = np.random.default_rng(0)
x = rng.normal(0, 1, 500)
snr = float(abs(x.mean()) / (x.std() / len(x) ** .5))
null = {"description": "media de ruido vs 0", "statistic": snr,
        "threshold": 3.0, "passed": bool(snr < 3.0)}
print("RESULT_JSON: " + json.dumps({
    "metrics": {"snr": snr, "n": 500},
    "null_test": null,
    "verdict": "refutes" if snr < 3.0 else "supports",
    "verdict_reason": "el ruido puro no supera el umbral del discriminador"}))
"""

NO_NULL_SUPPORTS = """
import json
print("RESULT_JSON: " + json.dumps({
    "metrics": {"x": 1.0}, "verdict": "supports", "verdict_reason": "sin nulos"}))
"""


def _plan_none(exp, hyp, domain):
    return {"data_urls": [], "analysis_outline": "análisis autocontenido"}


def test_happy_path_runs_real_code_in_sandbox():
    out = run_generated(EXP, HYP, plan=_plan_none,
                        codegen=lambda *a, **k: GOOD_SCRIPT)
    assert out["ok"] is True
    r = out["result"]
    assert r["verdict"] == "refutes"                # ruido puro NO apoya la señal
    assert r["metrics"]["n"] == 500
    assert out["attempts"] == 1
    # reproducible package on disk
    from pathlib import Path
    d = Path(out["artifacts_dir"])
    for f in ("script.py", "result.json", "stdout.txt", "run.sh"):
        assert (d / f).exists()


def test_repair_loop_recovers_from_crash():
    calls = {"n": 0}

    def flaky_codegen(exp, hyp, files, previews, feedback=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return "raise RuntimeError('boom generado')"
        assert feedback and "boom generado" in feedback   # error fed back to Codex
        return GOOD_SCRIPT

    out = run_generated(EXP, HYP, plan=_plan_none, codegen=flaky_codegen)
    assert out["ok"] is True and out["attempts"] == 2


def test_exhausted_repairs_fail_honestly_without_fabricating():
    out = run_generated(EXP, HYP, plan=_plan_none,
                        codegen=lambda *a, **k: "import sys; sys.exit(3)",
                        max_repairs=1)
    assert out["ok"] is False and out["stage"] == "run"
    assert "result" not in out                       # nunca inventa un resultado


def test_supports_without_null_test_is_downgraded():
    out = run_generated(EXP, HYP, plan=_plan_none,
                        codegen=lambda *a, **k: NO_NULL_SUPPORTS)
    assert out["ok"] is True
    assert out["result"]["verdict"] == "inconclusive"   # honestidad: sin nulos no hay apoyo
    assert "degradado por ACERO" in out["result"]["verdict_reason"]


def test_host_allowlist():
    assert _host_allowed("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?q=1")
    assert _host_allowed("https://www.sidc.be/SILSO/INFO/snmtotcsv.php")
    assert not _host_allowed("https://evil.example.com/data.csv")
    assert not _host_allowed("not-a-url")


def test_fetch_rejects_bad_urls(tmp_path):
    with pytest.raises(ValueError, match="HTTPS"):
        fetch_data([{"url": "http://sidc.be/x", "filename": "a", "what": ""}], tmp_path)
    with pytest.raises(ValueError, match="allowlist"):
        fetch_data([{"url": "https://evil.example.com/x.csv", "filename": "a",
                     "what": ""}], tmp_path)


def test_download_data_without_urls_fails_honestly():
    exp = dict(EXP, method_type="download_data")
    out = run_generated(exp, HYP, plan=_plan_none,
                        codegen=lambda *a, **k: GOOD_SCRIPT)
    assert out["ok"] is False and out["stage"] == "fetch"


def test_parse_result_validation():
    assert _parse_result("nada")[0] is None
    assert _parse_result('RESULT_JSON: {"metrics": {}}')[0] is None
    ok, _ = _parse_result('RESULT_JSON: {"metrics": {"a": 1}, '
                          '"verdict": "refutes", "verdict_reason": "x", '
                          '"null_test": {"description": "d", "passed": true}}')
    assert ok is not None and ok["verdict"] == "refutes"


def test_flow_uses_factory_result(session_factory, monkeypatch):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Fact", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]

    import acero.portal.experiment_factory as fx
    monkeypatch.setattr(fx, "run_generated", lambda exp, hyp, domain="", **k: {
        "ok": True, "result": {"metrics": {"m": 1.0},
                               "null_test": {"description": "d", "passed": True},
                               "verdict": "refutes", "verdict_reason": "nulos ganan"},
        "provenance": [{"url": "https://sidc.be/x", "filename": "f", "bytes": 10,
                        "sha256": "ab" * 32}],
        "attempts": 1, "code_path": "/tmp/x/script.py", "artifacts_dir": "/tmp/x",
        "duration_sec": 1.0, "generator": "codex+sandbox", "disclaimer": "d"})
    run = fl.run_experiment(p.id, e["id"], use_ai=True)
    assert run["mode"] == "generated_analysis"
    assert "CÓDIGO GENERADO POR IA" in run["claim"]
    stored = fl.store.get(e["id"])
    assert stored["status"] == "COMPLETE" and stored["synthetic"] is False
    assert stored["provenance"][0]["sha256"].startswith("ab")


def test_flow_factory_failure_falls_back_to_plan(session_factory, monkeypatch):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Fact2", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]

    import acero.portal.experiment_factory as fx
    monkeypatch.setattr(fx, "run_generated", lambda *a, **k: {
        "ok": False, "stage": "run", "error": "no válido", "attempts": 3})
    monkeypatch.setattr(HypothesisFlow, "_plan",
                        lambda self, ex, use_ai: "plan base offline")
    run = fl.run_experiment(p.id, e["id"], use_ai=True)
    assert run["mode"] == "plan_only"                  # honesto: plan, no resultado
    stored = fl.store.get(e["id"])
    assert stored["status"] == "PLANNED"
    assert stored["factory_error"]["stage"] == "run"   # y queda el porqué
