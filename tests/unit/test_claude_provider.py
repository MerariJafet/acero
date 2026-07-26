"""ClaudeCliProvider: build the right non-interactive command, clear the nested-session
guard, and parse the JSON envelope. Uses an injected runner (no real `claude` call)."""
from __future__ import annotations

import json

from acero.llm.providers import ClaudeCliProvider, get_provider


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
