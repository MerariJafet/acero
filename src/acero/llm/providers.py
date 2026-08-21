"""Concrete LLM providers: deterministic mock, Codex CLI, local Ollama, gated paid."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

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


def _parse_codex_jsonl(stdout: str) -> tuple[str, dict]:
    """Extract the final agent message and token usage from a ``codex exec --json`` stream.

    Returns (agent_text, usage_dict). Non-JSON lines (e.g. "Reading additional
    input from stdin...") are ignored. Robust to partial/garbled lines.
    """
    text = ""
    usage: dict = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = ev.get("type")
        if etype == "item.completed":
            item = ev.get("item", {})
            if item.get("type") == "agent_message" and item.get("text"):
                text = item["text"]
        elif etype == "turn.completed" and isinstance(ev.get("usage"), dict):
            usage = ev["usage"]
    return text, usage


def _codex_stream_error(stdout: str) -> str:
    """The error message from a codex stream that FAILED without a final message
    (e.g. `{"type":"error","message":"You've hit your usage limit..."}` or turn.failed).
    Empty string if no explicit error was reported."""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "error" and ev.get("message"):
            return str(ev["message"])
        if ev.get("type") == "turn.failed":
            err = ev.get("error") or {}
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])
    return ""


def _default_llm_timeout() -> int:
    """Per-call LLM timeout in seconds. The agent that DESIGNS experiments and writes
    scripts may legitimately take a long time (it only ever sees the schema + a 500-char
    preview, never the data), so we don't cut it short — only a truly hung call is killed.
    Default 1 hour; override with ACERO_LLM_TIMEOUT."""
    try:
        return max(30, int(os.environ.get("ACERO_LLM_TIMEOUT", "3600")))
    except ValueError:
        return 3600


def _fallback_to_claude_enabled() -> bool:
    """When Codex has no tokens / is unavailable, fall back to the `claude` CLI.
    Default ON; set ACERO_LLM_FALLBACK=none to disable."""
    return os.environ.get("ACERO_LLM_FALLBACK", "claude").strip().lower() not in {
        "none", "off", "0", ""}


_log = logging.getLogger("acero.llm")


def _note_fallback(exc: Exception) -> None:
    """Visible note: Codex failed / out of tokens → the science ran on Claude instead."""
    _log.warning("⚠️  Codex no disponible (%s) → usando Claude CLI como fallback",
                 str(exc)[:140])


class CodexCliProvider:
    """Local LLM provider that shells out to the Codex CLI (``codex exec``).

    Runs non-interactively in an ephemeral session with the safest sandbox
    (``read-only``) and no git-repo requirement. Uses ``--json`` to capture token
    usage (recorded for provenance/cost visibility) and ``--output-last-message``
    for clean final text. Model, params, command, and token usage are recorded;
    Codex output is a drafting aid, NEVER scientific evidence.

    Note: Codex authenticates via the user's own ``codex`` login and consumes their
    token quota. It is therefore NOT the default provider — it is selected
    explicitly (``ACERO_LLM_PROVIDER=codex``). ACERO does not manage its billing.
    """

    name = "codex"

    def __init__(
        self,
        command: str = "codex",
        model: str | None = None,
        *,
        sandbox: str = "read-only",
        timeout_sec: int | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.command = command
        self.model = model
        self.sandbox = sandbox
        self.timeout_sec = timeout_sec if timeout_sec is not None else _default_llm_timeout()
        self.extra_args = extra_args or []
        # Metadata from the most recent call, for provenance (usage, exit code, ...).
        self.last_usage: dict = {}
        self.last_params: dict = {}
        self._claude_fb: ClaudeCliProvider | None = None

    def _fallback(self) -> ClaudeCliProvider | None:
        """The Claude CLI provider to use when Codex has no tokens / is unavailable."""
        if not _fallback_to_claude_enabled():
            return None
        if self._claude_fb is None:
            fb = ClaudeCliProvider(model=self.model, timeout_sec=self.timeout_sec)
            self._claude_fb = fb if fb.available() else None
        return self._claude_fb

    def _codex_ok(self) -> bool:
        return shutil.which(self.command) is not None or Path(self.command).exists()

    def available(self) -> bool:
        # available if Codex is present OR we can fall back to Claude
        return self._codex_ok() or self._fallback() is not None

    def _build_cmd(
        self, prompt: str, last_message_file: str, output_schema_file: str | None = None
    ) -> list[str]:
        cmd = [
            self.command, "exec",
            "--json",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color", "never",
            "-s", self.sandbox,
            "--output-last-message", last_message_file,
        ]
        if output_schema_file:
            cmd += ["--output-schema", output_schema_file]
        if self.model:
            cmd += ["-m", self.model]
        cmd += self.extra_args
        cmd.append(prompt)
        return cmd

    def _run(self, prompt: str, output_schema_file: str | None = None) -> tuple[str, dict, list[str]]:
        if not self.available():
            raise CodexError(
                f"Codex CLI '{self.command}' not found on PATH. Install it or set "
                "the provider command explicitly."
            )
        with tempfile.TemporaryDirectory(prefix="acero_codex_") as tmp:
            last_file = str(Path(tmp) / "last_message.txt")
            cmd = self._build_cmd(prompt, last_file, output_schema_file)
            try:
                proc = subprocess.run(
                    cmd, cwd=tmp, capture_output=True, text=True,
                    timeout=self.timeout_sec, stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired as exc:
                raise CodexError(f"Codex CLI timed out after {self.timeout_sec}s") from exc

            json_text, usage = _parse_codex_jsonl(proc.stdout or "")
            # Prefer the last-message file (cleanest); fall back to the JSON stream.
            text = ""
            if Path(last_file).exists():
                text = Path(last_file).read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                text = json_text.strip()
            if not text:
                # empty result — surface the real cause (usage limit / error) so callers
                # (and the Codex→Claude fallback) can act instead of silently stubbing.
                err = (_codex_stream_error(proc.stdout or "")
                       or (proc.stderr or "").strip())
                raise CodexError(f"Codex sin salida (exit {proc.returncode}): "
                                 f"{err[:400]}")
            params = {
                "sandbox": self.sandbox,
                "command": " ".join(cmd[:-1]) + " <prompt>",
                "exit_code": proc.returncode,
                "usage": usage,
            }
            self.last_usage = usage
            self.last_params = params
            return text, params, cmd

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:
        if not self._codex_ok():
            fb = self._fallback()
            if fb is not None:
                return fb.complete(prompt, temperature=temperature, max_tokens=max_tokens)
        try:
            text, params, _ = self._run(prompt)
        except CodexError as exc:
            fb = self._fallback()                    # no tokens / error → Claude
            if fb is None:
                raise
            _note_fallback(exc)
            return fb.complete(prompt, temperature=temperature, max_tokens=max_tokens)
        params["max_tokens"] = max_tokens
        return LLMResponse(
            text=text, provider=self.name, model=self.model or "codex-default",
            temperature=temperature, params=params,
        )

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0) -> dict:
        """Return a validated JSON object conforming to ``schema`` via --output-schema.

        Enables structured agent outputs (hypothesis generator, skeptic). Raises
        CodexError if the model's final message is not valid JSON.
        """
        if not self._codex_ok():
            fb = self._fallback()
            if fb is not None:
                return fb.complete_json(prompt, schema, temperature=temperature)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", prefix="acero_schema_", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(schema, fh)
            schema_path = fh.name
        try:
            text, _, _ = self._run(prompt, output_schema_file=schema_path)
        except CodexError as exc:
            fb = self._fallback()                    # no tokens / error → Claude
            if fb is None:
                raise
            _note_fallback(exc)
            return fb.complete_json(prompt, schema, temperature=temperature)
        finally:
            Path(schema_path).unlink(missing_ok=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise CodexError(f"Codex did not return valid JSON: {text[:300]}") from exc


class ClaudeError(RuntimeError):
    pass


def _is_auth_error(msg: str) -> bool:
    """¿El CLI falló porque la SESIÓN está muerta (401/token revocado)?

    Distinguir esto de cualquier otro error importa: un token revocado no se
    arregla reintentando — solo lo arregla un humano con `claude login`."""
    low = (msg or "").lower()
    return ("revoked" in low or "401" in low or "authentication_error" in low
            or "failed to authenticate" in low or "unauthorized" in low)


def _claude_session_dead() -> bool:
    """El cortacircuitos compartido con el agente enjaulado: si la sesión del
    CLI ya se marcó muerta y NADIE se ha vuelto a loguear desde entonces, ni
    intentarlo. Se cierra solo cuando cambian las credenciales."""
    try:
        from ..sandbox.agentic_runner import agent_breaker_open
        return agent_breaker_open()
    except Exception:  # noqa: BLE001 - el breaker jamás rompe una corrida
        return False


class ClaudeCliProvider:
    """Local LLM provider that shells out to the `claude` CLI (Claude Code) in print mode.

    Lets ACERO run the SCIENCE on Claude instead of Codex, so agents are not mixed
    (`ACERO_LLM_PROVIDER=claude`). Runs non-interactively (`-p --output-format json`),
    without session persistence, and UNSETS the CLAUDECODE guard so it works even when
    ACERO is itself launched from a Claude Code session. Claude output is a drafting aid,
    NEVER scientific evidence — same rule as Codex.

    Note: `claude` cannot be nested inside a live Claude Code session (the CLI blocks it);
    this provider clears CLAUDECODE for the child, so it runs cleanly from a normal shell,
    a portal process, or a cron. Auth uses the user's own `claude` login.
    """

    name = "claude"

    def __init__(self, command: str = "claude", model: str | None = None, *,
                 timeout_sec: int | None = None, extra_args: list[str] | None = None,
                 runner: Any | None = None) -> None:
        self.command = command
        self.model = model
        self.timeout_sec = timeout_sec if timeout_sec is not None else _default_llm_timeout()
        self.extra_args = extra_args or []
        self._runner = runner            # injectable (cmd, env) -> (stdout, stderr, rc)
        self.last_usage: dict = {}
        self.last_params: dict = {}

    def available(self) -> bool:
        # 2026-08-21: con el token revocado, ACERO llamó al CLI ~300 veces en un
        # día — un 401 por experimento, ~10 h "planeando" lo que nadie podía
        # ejecutar. El breaker convierte eso en una sola avería visible.
        if _claude_session_dead():
            return False
        return shutil.which(self.command) is not None or Path(self.command).exists()

    def _build_cmd(self, prompt: str) -> list[str]:
        # `--tools ""` disables ALL of Claude Code's agentic tools so it behaves as a
        # PURE text generator. Without this, `claude -p` acts as an agent: it writes/runs
        # files itself and returns a PROSE SUMMARY instead of the raw script — which broke
        # ACERO's codegen (the summary was saved as script.py and failed in the sandbox).
        cmd = [self.command, "-p", prompt, "--output-format", "json",
               "--tools", "", "--dangerously-skip-permissions", "--no-session-persistence"]
        if self.model:
            cmd += ["--model", self.model]
        return cmd + self.extra_args

    def _child_env(self) -> dict[str, str]:
        # Make `claude` run as an INDEPENDENT CLI: clear the nested-session guard AND the
        # host-managed auth redirection (ANTHROPIC_BASE_URL + SDK refresh vars). Otherwise
        # it either refuses ("nested session") or hangs trying to use the host proxy that
        # only the desktop app can refresh. Forcing standalone auth means it works anywhere
        # `claude login` is valid, and fails FAST+CLEAR (401) if the token is revoked.
        env = dict(os.environ)
        for k in ("CLAUDECODE", "CLAUDE_CODE_SSE_PORT", "CLAUDE_CODE_ENTRYPOINT",
                  "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ID",
                  "ANTHROPIC_BASE_URL"):
            env.pop(k, None)
        return env

    def _run(self, prompt: str) -> tuple[str, dict]:
        if not self.available():
            raise ClaudeError(f"claude CLI '{self.command}' not found on PATH.")
        cmd = self._build_cmd(prompt)
        if self._runner is not None:
            stdout, stderr, rc = self._runner(cmd, self._child_env())
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout_sec, stdin=subprocess.DEVNULL,
                                  env=self._child_env())
            stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        text, usage, err = self._parse(stdout or "")
        if err:
            auth = _is_auth_error(err)
            if auth:
                try:
                    from ..sandbox.agentic_runner import mark_agent_unauthenticated
                    mark_agent_unauthenticated(err)
                except Exception:  # noqa: BLE001
                    pass
            hint = " — corre `claude login` para renovar la sesión" if auth else ""
            raise ClaudeError(f"claude CLI error: {err[:300]}{hint}")
        if rc != 0 and not text:
            raise ClaudeError(f"claude CLI exited {rc}: {(stderr or '').strip()[:500]}")
        params = {"command": " ".join(cmd[:2]) + " <prompt> …", "exit_code": rc,
                  "usage": usage}
        self.last_usage, self.last_params = usage, params
        return text, params

    @staticmethod
    def _parse(stdout: str) -> tuple[str, dict, str]:
        """`claude --output-format json` emits one result envelope: {type:result,
        is_error:bool, result:<text|error msg>, usage:{...}}. Returns
        (text, usage, error) — `error` non-empty when the CLI reported a failure
        (e.g. revoked auth) so it is raised, not returned as if it were an answer."""
        try:
            obj = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return stdout.strip(), {}, ""
        if isinstance(obj, dict):
            result = str(obj.get("result", "")).strip()
            if obj.get("is_error"):
                return "", obj.get("usage", {}) or {}, result or "claude reportó error"
            return result, obj.get("usage", {}) or {}, ""
        return stdout.strip(), {}, ""

    def complete(self, prompt: str, *, temperature: float = 0.0,
                 max_tokens: int = 1024) -> LLMResponse:
        text, params = self._run(prompt)
        params["max_tokens"] = max_tokens
        return LLMResponse(text=text, provider=self.name,
                           model=self.model or "claude-default",
                           temperature=temperature, params=params)

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0) -> dict:
        """No native --output-schema: ask for JSON-only and parse the first object."""
        keys = ", ".join((schema.get("properties") or {}).keys())
        text, _ = self._run(
            prompt + f"\n\nResponde SOLO con un objeto JSON válido con las claves: {keys}. "
            "Sin markdown, sin texto extra.")
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise ClaudeError(f"claude did not return valid JSON: {cleaned[:300]}") from None


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
    if name == "claude":
        return ClaudeCliProvider(
            command=kwargs.get("command", "claude"), model=kwargs.get("model"))
    if name == "openai":
        return PaidProvider(name, guard)
    return MockProvider()
