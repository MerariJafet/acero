"""Agentic experiment role — jailed authoring + net-free scoring + reproduce-check.

All offline: the container runner and the AgenticAuthor are injected, so no real
docker/claude call happens. The SCORED run is forced onto the subprocess sandbox
by disabling docker, so the tests are hermetic on any machine."""
from __future__ import annotations

import json

import pytest

from acero.portal.experiment_factory import (
    build_agentic_prompt,
    experiment_agent_enabled,
    run_generated,
)
from acero.sandbox.agentic_runner import AgenticAuthor, AgenticResult, agent_available

EXP = {"id": "exp_ag1", "title": "prueba agéntica", "what": "w", "how": "h",
       "data_source": "sintético", "controls": "shuffle",
       "discriminator": "slope!=0", "method_type": "simulation"}
HYP = {"title": "hipótesis agéntica"}

DET_SCRIPT = (
    "import json\n"
    "print('RESULT_JSON: ' + json.dumps({"
    "'metrics': {'slope': 2.0}, "
    "'null_test': {'description': 'permuto y', 'statistic': 0.01, "
    "'threshold': 0.05, 'passed': True}, "
    "'verdict': 'refutes', 'verdict_reason': 'determinista'}))\n"
)


DET_SUPPORTS = (
    "import json\n"
    "print('RESULT_JSON: ' + json.dumps({"
    "'metrics': {'slope': 2.0}, "
    "'null_test': {'description': 'permuto y', 'statistic': 0.001, "
    "'threshold': 0.05, 'passed': True}, "
    "'verdict': 'supports', 'verdict_reason': 'determinista supports'}))\n"
)


def _plan_none(exp, hyp, domain):
    return {"data_urls": [], "analysis_outline": "autocontenido"}


class _MultiCallAuthor:
    """Primary call and cross-check call return the SAME scored script but DIFFERENT
    claimed dicts — used to prove the reproduce-check reads the PRIMARY claim."""

    def __init__(self):
        self.calls = 0

    def author(self, prompt: str, workdir) -> AgenticResult:
        self.calls += 1
        claimed = ({"metrics": {"slope": 2.0}, "verdict": "supports"} if self.calls == 1
                   else {"metrics": {"slope": 99.0}, "verdict": "supports"})
        return AgenticResult(ok=True, code=DET_SUPPORTS, claimed=claimed,
                             raw="x", num_turns=2, cost_usd=0.1, duration_sec=1.0)


class _FakeAuthor:
    """Stands in for AgenticAuthor: returns a fixed script + a claimed result."""

    def __init__(self, code: str, claimed: dict | None):
        self.code = code
        self.claimed = claimed
        self.calls = 0

    def author(self, prompt: str, workdir) -> AgenticResult:
        self.calls += 1
        return AgenticResult(ok=True, code=self.code, claimed=self.claimed,
                             raw="resumen del agente", num_turns=4, cost_usd=0.12,
                             duration_sec=3.0)


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    # scored run must NOT touch docker → force the subprocess sandbox fallback
    monkeypatch.setattr("acero.sandbox.docker_runner.docker_available", lambda: False)
    monkeypatch.setenv("ACERO_EXPERIMENT_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ACERO_EXPERIMENT_AGENT", "1")


# --- integration through the factory -----------------------------------------

def test_agent_authors_and_result_is_scored_net_free():
    claimed = {"metrics": {"slope": 2.0}, "verdict": "refutes",
               "verdict_reason": "afirmado por el agente"}
    author = _FakeAuthor(DET_SCRIPT, claimed)
    out = run_generated(EXP, HYP, plan=_plan_none, author=author, verify_supports=False)
    assert out["ok"] is True
    assert author.calls == 1
    res = out["result"]
    # the SCORED number came from the net-free run of the agent's script
    assert res["metrics"]["slope"] == 2.0
    ag = res["agentic"]
    assert ag["authored_by"] == "claude-agentic"
    assert ag["reproduced"] is True                 # claimed == scored
    assert "subprocess" in ag["scored_in"]          # docker disabled in this test
    assert ag["cost_usd"] == pytest.approx(0.12)


def test_reproduce_mismatch_raises_integrity_flag():
    # the agent CLAIMS a wildly different, opposite result than its own script yields
    claimed = {"metrics": {"slope": 99.0}, "verdict": "supports",
               "verdict_reason": "afirmación inflada"}
    author = _FakeAuthor(DET_SCRIPT, claimed)
    out = run_generated(EXP, HYP, plan=_plan_none, author=author, verify_supports=False)
    res = out["result"]
    assert res["metrics"]["slope"] == 2.0           # net-free truth stands
    assert res["agentic"]["reproduced"] is False
    assert "integridad ACERO" in res["verdict_reason"]


def test_reproduce_check_uses_primary_claim_not_crosscheck():
    # cross-check re-invokes the agent; the reproduce-check must compare against
    # the PRIMARY implementation's claim, not the second implementation's.
    author = _MultiCallAuthor()
    out = run_generated(EXP, HYP, plan=_plan_none, author=author, verify_supports=True)
    assert author.calls >= 2                         # primary + cross-check
    res = out["result"]
    assert res["metrics"]["slope"] == 2.0
    # primary claim (slope 2.0) reproduces the net-free score → True, NOT the
    # second implementation's inflated claim (slope 99.0)
    assert res["agentic"]["reproduced"] is True
    assert "integridad ACERO" not in res.get("verdict_reason", "")


def test_explicit_codegen_forces_non_agent_path():
    out = run_generated(EXP, HYP, plan=_plan_none, codegen=lambda *a, **k: DET_SCRIPT,
                        verify_supports=False)
    assert out["ok"] is True
    assert "agentic" not in out["result"]           # pure-completion path


# --- AgenticAuthor unit (injected container runner) ---------------------------

def _fake_home(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".credentials.json").write_text("{}")
    (home / ".claude.json").write_text("{}")
    return home


def test_author_reads_script_and_parses_claimed(tmp_path, monkeypatch):
    monkeypatch.setattr("acero.sandbox.agentic_runner._host_home",
                        lambda: _fake_home(tmp_path))
    ws = tmp_path / "ws"
    ws.mkdir()

    def runner(cmd, timeout):
        # the container would write analysis.py; simulate that side effect
        (ws / "analysis.py").write_text("print('RESULT_JSON: {\"metrics\": {\"a\": 1}}')")
        env = {"is_error": False, "num_turns": 3, "total_cost_usd": 0.2,
               "result": 'listo. RESULT_JSON: {"metrics": {"a": 1}, "verdict": "supports"}'}
        return json.dumps(env), "", 0

    r = AgenticAuthor(runner=runner).author("prompt", ws)
    assert r.ok is True and r.num_turns == 3
    assert "analysis.py" not in r.code and "RESULT_JSON" in r.code
    assert r.claimed == {"metrics": {"a": 1}, "verdict": "supports"}
    assert not (ws / ".agent_home").exists()        # credentials wiped after run


def test_author_flags_agent_error(tmp_path, monkeypatch):
    monkeypatch.setattr("acero.sandbox.agentic_runner._host_home",
                        lambda: _fake_home(tmp_path))
    ws = tmp_path / "ws2"
    ws.mkdir()

    def runner(cmd, timeout):
        return json.dumps({"is_error": True, "result": "Not logged in"}), "", 0

    r = AgenticAuthor(runner=runner).author("p", ws)
    assert r.ok is False and "Not logged in" in r.error


def test_author_flags_missing_script(tmp_path, monkeypatch):
    monkeypatch.setattr("acero.sandbox.agentic_runner._host_home",
                        lambda: _fake_home(tmp_path))
    ws = tmp_path / "ws3"
    ws.mkdir()

    def runner(cmd, timeout):
        return json.dumps({"is_error": False, "result": "no escribí nada"}), "", 0

    r = AgenticAuthor(runner=runner).author("p", ws)
    assert r.ok is False and "analysis.py" in r.error


def test_author_tolerates_non_json_output(tmp_path, monkeypatch):
    monkeypatch.setattr("acero.sandbox.agentic_runner._host_home",
                        lambda: _fake_home(tmp_path))
    ws = tmp_path / "ws4"
    ws.mkdir()
    r = AgenticAuthor(runner=lambda cmd, t: ("basura no-json", "boom", 1)).author("p", ws)
    assert r.ok is False


def test_build_agentic_prompt_carries_contract_and_addendum():
    p = build_agentic_prompt(EXP, HYP, [], {})
    assert "RESULT_JSON" in p and "MODO AGÉNTICO" in p and "./analysis.py" in p


def test_agent_enabled_toggle(monkeypatch):
    monkeypatch.setenv("ACERO_EXPERIMENT_AGENT", "0")
    assert experiment_agent_enabled() is False
    monkeypatch.setenv("ACERO_EXPERIMENT_AGENT", "1")
    assert experiment_agent_enabled() is True


def test_agent_available_false_without_creds(tmp_path, monkeypatch):
    monkeypatch.setattr("acero.sandbox.agentic_runner._host_home", lambda: tmp_path)
    assert agent_available() is False               # no creds under this home
