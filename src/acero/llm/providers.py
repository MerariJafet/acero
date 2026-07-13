"""Concrete LLM providers: deterministic mock, Codex CLI, local Ollama, gated paid."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..core.errors import PolicyViolation
from ..policies.guard import PolicyGuard
from .base import LLMResponse


class MockProvider:
    """Deterministic, offline provider. Default in tests and this session.

    Produces a stable, inspectable pseudo-response derived from the prompt hash so
    behaviour is reproducible without any network or model.
    """

    name = "mock"

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        text = (
            f"[MOCK:{digest}] Deterministic placeholder response. "
            "This text is a drafting aid, NOT scientific evidence."
        )
        return LLMResponse(
            text=text, provider=self.name, model="mock-1",
            temperature=temperature, params={"max_tokens": max_tokens, "prompt_sha": digest},
        )


class OllamaProvider:
    """Local Ollama adapter. Active only if the daemon is reachable."""

    name = "ollama"

    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "llama3.1") -> None:
        self.host = host
        self.model = model

    def available(self) -> bool:  # pragma: no cover - depends on local daemon
        try:
            import httpx

            r = httpx.get(f"{self.host}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:  # pragma: no cover - network/daemon gated
        import httpx

        payload = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = httpx.post(f"{self.host}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        data = json.loads(r.text)
        return LLMResponse(
            text=data.get("response", ""), provider=self.name, model=self.model,
            temperature=temperature, params={"max_tokens": max_tokens},
        )


class CodexError(RuntimeError):
    """Codex CLI invocation failed."""


class CodexCliProvider:
    """Local LLM provider that shells out to the Codex CLI (``codex exec``).

    Runs non-interactively in an ephemeral session with the safest sandbox
    (``read-only``) and no git-repo requirement. The agent's final message is read
    from ``--output-last-message`` for clean text. Model, params, and the invoked
    command are recorded for provenance; Codex output is a drafting aid, never
    scientific evidence.

    Note: Codex authenticates via the user's own ``codex`` login and may reach a
    remote backend. It is therefore NOT the default provider — it is selected
    explicitly (``ACERO_LLM_PROVIDER=codex``). ACERO does not manage its billing.
    """

    name = "codex"

    def __init__(
        self,
        command: str = "codex",
        model: str | None = None,
        *,
        sandbox: str = "read-only",
        timeout_sec: int = 300,
        extra_args: list[str] | None = None,
    ) -> None:
        self.command = command
        self.model = model
        self.sandbox = sandbox
        self.timeout_sec = timeout_sec
        self.extra_args = extra_args or []

    def available(self) -> bool:
        return shutil.which(self.command) is not None or Path(self.command).exists()

    def _build_cmd(self, prompt: str, last_message_file: str) -> list[str]:
        cmd = [
            self.command, "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color", "never",
            "-s", self.sandbox,
            "--output-last-message", last_message_file,
        ]
        if self.model:
            cmd += ["-m", self.model]
        cmd += self.extra_args
        cmd.append(prompt)
        return cmd

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:
        if not self.available():
            raise CodexError(
                f"Codex CLI '{self.command}' not found on PATH. Install it or set "
                "the provider command explicitly."
            )
        with tempfile.TemporaryDirectory(prefix="acero_codex_") as tmp:
            last_file = str(Path(tmp) / "last_message.txt")
            cmd = self._build_cmd(prompt, last_file)
            try:
                proc = subprocess.run(
                    cmd, cwd=tmp, capture_output=True, text=True, timeout=self.timeout_sec,
                )
            except subprocess.TimeoutExpired as exc:
                raise CodexError(f"Codex CLI timed out after {self.timeout_sec}s") from exc
            text = ""
            if Path(last_file).exists():
                text = Path(last_file).read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                # Fall back to stdout if the last-message file was not written.
                text = (proc.stdout or "").strip()
            if proc.returncode != 0 and not text:
                raise CodexError(
                    f"Codex CLI exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}"
                )
            return LLMResponse(
                text=text, provider=self.name, model=self.model or "codex-default",
                temperature=temperature,
                params={
                    "max_tokens": max_tokens, "sandbox": self.sandbox,
                    "command": " ".join(cmd[:-1]) + " <prompt>", "exit_code": proc.returncode,
                },
            )


class PaidProvider:
    """Placeholder for Claude/OpenAI API. Refuses unless policy enables paid services."""

    def __init__(self, name: str, guard: PolicyGuard) -> None:
        self.name = name
        self._guard = guard

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        if not self._guard.paid_llm_allowed():
            raise PolicyViolation(
                f"Paid provider '{self.name}' is disabled (external_paid_services=false). "
                "Human approval and a raised cost limit are required to enable it."
            )
        raise NotImplementedError(  # pragma: no cover
            f"'{self.name}' client intentionally not wired in this local-first build."
        )


def get_provider(name: str, guard: PolicyGuard | None = None, **kwargs):
    guard = guard or PolicyGuard()
    if name == "mock":
        return MockProvider()
    if name == "codex":
        return CodexCliProvider(
            command=kwargs.get("command", "codex"),
            model=kwargs.get("model"),
            sandbox=kwargs.get("sandbox", "read-only"),
        )
    if name == "ollama":
        return OllamaProvider(
            host=kwargs.get("host", "http://127.0.0.1:11434"),
            model=kwargs.get("model", "llama3.1"),
        )
    if name in {"claude", "openai"}:
        return PaidProvider(name, guard)
    return MockProvider()
