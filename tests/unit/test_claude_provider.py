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


# --- guardia anti-carrera de refresco (causa raíz de la caída del 21/08) ------
# El pool corre varios `claude -p` a la vez compartiendo UN archivo de
# credenciales. El refresh token es de UN SOLO USO: refrescar en paralelo hace
# que el servidor detecte reuso y revoque la familia entera. La guardia
# serializa las llamadas SOLO cuando el token está por vencer.

import os
import threading
import time as _time

from pathlib import Path


def _escribir_creds(expira_en_seg):
    p = Path(os.environ["ACERO_CLAUDE_CREDS"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"claudeAiOauth": {
        "expiresAt": int((_time.time() + expira_en_seg) * 1000)}}))
    return p


def _runner_lento(marcas, dur=0.15):
    """Runner que registra ventanas [inicio, fin] para detectar solape."""
    def run(cmd, env):
        t0 = _time.monotonic()
        _time.sleep(dur)
        marcas.append((t0, _time.monotonic()))
        return json.dumps({"type": "result", "result": "ok", "usage": {}}), "", 0
    return run


def test_con_token_por_vencer_las_llamadas_se_serializan():
    _escribir_creds(expira_en_seg=60)          # < margen de 900 s → guardia activa
    marcas = []
    p = ClaudeCliProvider(runner=_runner_lento(marcas))
    hilos = [threading.Thread(target=p.complete, args=("x",)) for _ in range(3)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    marcas.sort()
    for (_, fin_a), (ini_b, _) in zip(marcas, marcas[1:]):
        assert ini_b >= fin_a, "dos llamadas al CLI se solaparon con el token por vencer"


def test_con_token_fresco_no_se_serializa_nada():
    _escribir_creds(expira_en_seg=7200)        # 2 h de vida → sin candado
    marcas = []
    p = ClaudeCliProvider(runner=_runner_lento(marcas))
    hilos = [threading.Thread(target=p.complete, args=("x",)) for _ in range(3)]
    t0 = _time.monotonic()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    total = _time.monotonic() - t0
    # 3 llamadas de 0.15 s en paralelo deben tardar MUCHO menos que 3×0.15 s
    assert total < 0.40, f"las llamadas se serializaron con el token fresco ({total:.2f}s)"


def test_sin_archivo_de_credenciales_no_hay_candado_ni_crash():
    Path(os.environ["ACERO_CLAUDE_CREDS"]).unlink(missing_ok=True)
    p = ClaudeCliProvider(runner=_runner_ok("ok"))
    assert p.complete("x").text == "ok"
