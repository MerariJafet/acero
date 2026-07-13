"""Codex CLI provider tests using a fake `codex` shim (no real/paid invocation)."""

from __future__ import annotations

import stat

import pytest

from acero.llm.providers import CodexCliProvider, CodexError

FAKE_CODEX = """#!/usr/bin/env python3
import sys
# Emulate: codex exec ... --output-last-message <FILE> ... <PROMPT>
args = sys.argv[1:]
last_file = None
for i, a in enumerate(args):
    if a == "--output-last-message":
        last_file = args[i + 1]
prompt = args[-1]
msg = "CODEX_REPLY: " + prompt[:40]
if last_file:
    with open(last_file, "w") as fh:
        fh.write(msg)
print("[codex] session log line (ignored)")
"""


@pytest.fixture()
def fake_codex(tmp_path):
    script = tmp_path / "codex"
    script.write_text(FAKE_CODEX)
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(script)


def test_codex_available_detects_binary(fake_codex):
    prov = CodexCliProvider(command=fake_codex)
    assert prov.available()


def test_codex_missing_binary_raises():
    prov = CodexCliProvider(command="definitely-not-a-real-binary-xyz")
    assert not prov.available()
    with pytest.raises(CodexError):
        prov.complete("hello")


def test_codex_reads_last_message(fake_codex):
    prov = CodexCliProvider(command=fake_codex, model="gpt-x")
    r = prov.complete("Explain Newton cooling briefly")
    assert r.provider == "codex"
    assert r.model == "gpt-x"
    assert r.text.startswith("CODEX_REPLY: Explain Newton cooling")
    assert r.is_evidence is False           # never treated as evidence
    assert "read-only" in r.params["sandbox"]
    assert r.params["exit_code"] == 0


def test_codex_builds_hardened_command(fake_codex):
    prov = CodexCliProvider(command=fake_codex)
    cmd = prov._build_cmd("PROMPT", "/tmp/last.txt")
    assert "--skip-git-repo-check" in cmd
    assert "--ephemeral" in cmd
    assert "-s" in cmd and "read-only" in cmd
    assert cmd[-1] == "PROMPT"


def test_get_provider_returns_codex():
    from acero.llm.providers import get_provider

    assert get_provider("codex").name == "codex"


def test_factory_builds_codex_from_config(monkeypatch):
    monkeypatch.setenv("ACERO_LLM_PROVIDER", "codex")
    monkeypatch.setenv("ACERO_CODEX_COMMAND", "codex")
    from acero.core.config import load_config
    from acero.llm.factory import provider_from_config

    cfg = load_config()
    prov = provider_from_config(cfg)
    assert prov.name == "codex"
    assert prov.command == "codex"
