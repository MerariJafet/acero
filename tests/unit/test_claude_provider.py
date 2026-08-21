"""ClaudeCliProvider: build the right non-interactive command, clear the nested-session
guard, and parse the JSON envelope. Uses an injected runner (no real `claude` call)."""
from __future__ import annotations

import json

from acero.llm.base import LLMResponse
from acero.llm.providers import (
    ClaudeCliProvider,
    CodexCliProvider,
    CodexError,
    _codex_stream_error,
    get_provider,
)


def _runner_ok(result_text):
    def run(cmd, env):
        return json.dumps({"type": "result", "result": result_text,
                           "usage": {"input_tokens": 5}}), "", 0
    return run


def test_build_cmd_is_non_interactive_and_clears_guard():
    p = ClaudeCliProvider(model="opus", runner=_runner_ok("x"))
    cmd = p._build_cmd("hola")
    assert cmd[:2] == ["claude", "-p"]
    assert "--output-format" in cmd and "json" in cmd
    assert "--dangerously-skip-permissions" in cmd and "--no-session-persistence" in cmd
    assert "--tools" in cmd                        # agentic tools disabled → pure codegen
    assert "--model" in cmd and "opus" in cmd
    import os
    os.environ["CLAUDECODE"] = "1"
    assert "CLAUDECODE" not in p._child_env()      # nested-session guard cleared


def test_complete_parses_result_envelope():
    p = ClaudeCliProvider(runner=_runner_ok("VIVO"))
    r = p.complete("di algo")
    assert r.text == "VIVO" and r.provider == "claude"


def test_complete_json_parses_object_with_fences():
    def run(cmd, env):
        return json.dumps({"type": "result",
                           "result": "```json\n{\"a\": 1, \"b\": 2}\n```"}), "", 0
    p = ClaudeCliProvider(runner=run)
    out = p.complete_json("dame json", {"properties": {"a": {}, "b": {}}})
    assert out == {"a": 1, "b": 2}


def test_parse_falls_back_to_raw_when_not_json():
    assert ClaudeCliProvider._parse("just text")[0] == "just text"


def test_get_provider_returns_claude_cli():
    assert isinstance(get_provider("claude"), ClaudeCliProvider)



class _FakeClaude:
    def __init__(self):
        self.calls = []

    def complete(self, prompt, *, temperature=0.0, max_tokens=1024):
        self.calls.append("complete")
        return LLMResponse(text="CLAUDE", provider="claude", model="c",
                           temperature=0.0, params={})

    def complete_json(self, prompt, schema, *, temperature=0.0):
        self.calls.append("json")
        return {"via": "claude"}


def test_detects_usage_limit_in_stream():
    line = '{"type":"error","message":"You\'ve hit your usage limit."}'
    assert "usage limit" in _codex_stream_error(line)
    line2 = '{"type":"turn.failed","error":{"message":"quota"}}'
    assert _codex_stream_error(line2) == "quota"


def test_codex_falls_back_to_claude_on_error(monkeypatch):
    p = CodexCliProvider()
    monkeypatch.setattr(p, "_codex_ok", lambda: True)

    def boom(*a, **k):
        raise CodexError("Codex sin salida: usage limit")
    monkeypatch.setattr(p, "_run", boom)
    fake = _FakeClaude()
    p._claude_fb = fake
    r = p.complete("hola")
    assert r.text == "CLAUDE" and fake.calls == ["complete"]
    out = p.complete_json("dame json", {"properties": {"a": {}}})
    assert out == {"via": "claude"}


def test_no_fallback_when_disabled(monkeypatch):
    monkeypatch.setenv("ACERO_LLM_FALLBACK", "none")
    p = CodexCliProvider()
    monkeypatch.setattr(p, "_codex_ok", lambda: True)

    def boom(*a, **k):
        raise CodexError("usage limit")
    monkeypatch.setattr(p, "_run", boom)
    import pytest
    with pytest.raises(CodexError):
        p.complete("hola")


# --- sesión revocada: fallar UNA vez, no 300 -----------------------------------

def _runner_401(cmd, env):
    return json.dumps({
        "type": "result", "subtype": "error_during_execution",
        "is_error": True,
        "result": ('API Error: 401 {"type":"error","error":'
                   '{"type":"authentication_error",'
                   '"message":"OAuth access token has been revoked."}}'),
    }), "", 1


def test_token_revocado_abre_el_cortacircuitos(tmp_path, monkeypatch):
    """El 2026-08-21 el token quedó revocado y ACERO llamó al CLI ~300 veces:
    un 401 por experimento, ~10 h 'planeando' lo que nadie podía ejecutar. Un
    fallo de credenciales NO se arregla reintentando — solo con `claude login`."""
    import pytest
    from acero.llm.providers import ClaudeError
    from acero.sandbox import agentic_runner as ar

    monkeypatch.setenv("ACERO_AGENT_BREAKER", str(tmp_path / "breaker.json"))
    p = ClaudeCliProvider(runner=_runner_401)
    assert p.available() is True                  # antes del fallo, disponible
    with pytest.raises(ClaudeError):
        p.complete("hola")
    assert ar.agent_breaker_open() is True         # la avería quedó registrada
    assert p.available() is False                  # y ya nadie vuelve a intentar


def test_un_error_normal_NO_abre_el_cortacircuitos(tmp_path, monkeypatch):
    """Solo la sesión muerta corta: un timeout o un error de prompt son
    reintentables, y apagar el proveedor por ellos sería peor que el fallo."""
    import pytest
    from acero.llm.providers import ClaudeError
    from acero.sandbox import agentic_runner as ar

    monkeypatch.setenv("ACERO_AGENT_BREAKER", str(tmp_path / "breaker.json"))

    def run(cmd, env):
        return json.dumps({"type": "result", "is_error": True,
                           "result": "context window exceeded"}), "", 1
    p = ClaudeCliProvider(runner=run)
    with pytest.raises(ClaudeError):
        p.complete("hola")
    assert ar.agent_breaker_open() is False
