"""Agentic authoring backend for ACERO's experiment role.

The agent (Claude Code CLI) runs INSIDE a container (``acero-agent`` image) WITH
network — it needs the Anthropic API — and AUTHORS + debugs an analysis script
against the experiment's data. It is confined by the container + ``--add-dir``
to ``/work`` and cannot see the host.

Its output is NOT trusted as evidence. ACERO re-runs the authored script in the
``--network=none`` scored sandbox (``DockerRunner``) and cross-checks that the
agent's claimed ``RESULT_JSON`` reproduces there. See ``experiment_factory`` for
that scoring + reproduce-check. This module only handles the *authoring* run.

Auth: the host's Claude credentials (``~/.claude/.credentials.json`` — OAuth —
and ``~/.claude.json``, which carries ``oauthAccount``) are copied into a
per-run HOME that is bind-mounted read-write, and the container runs as the host
``uid:gid`` so it can read them (the files are ``0600``). No host env is passed
in, so no secrets leak by construction beyond the copied credentials.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_AGENT_IMAGE = os.environ.get("ACERO_AGENT_IMAGE", "acero-agent:py312")
# The agent may legitimately take a long time (write → run → debug → re-run).
# Only a truly hung run should fail; default 1h, override with the env var.
DEFAULT_AGENT_TIMEOUT = max(60, int(os.environ.get("ACERO_AGENT_TIMEOUT", "3600")))
SCRIPT_NAME = "analysis.py"

_RESULT_RE = re.compile(r"RESULT_JSON:\s*(\{.*\})", re.DOTALL)


def _host_home() -> Path:
    return Path(os.environ.get("ACERO_CLAUDE_HOME", str(Path.home())))


def _creds_present() -> bool:
    home = _host_home()
    return (home / ".claude" / ".credentials.json").exists() and (home / ".claude.json").exists()


def _creds_fingerprint() -> str:
    """Huella de las credenciales EN DISCO (mtime+tamaño). Cambia cuando el humano
    vuelve a loguearse — es la señal de que vale la pena reintentar."""
    home = _host_home()
    parts = []
    for f in (home / ".claude" / ".credentials.json", home / ".claude.json"):
        try:
            st = f.stat()
            parts.append(f"{int(st.st_mtime)}:{st.st_size}")
        except Exception:  # noqa: BLE001
            parts.append("-")
    return "|".join(parts)


def _breaker_file() -> Path:
    env = os.environ.get("ACERO_AGENT_BREAKER", "").strip()
    if env:
        return Path(env)
    return _host_home() / ".acero_agent_breaker.json"


def mark_agent_unauthenticated(error: str = "") -> None:
    """Abre el cortacircuitos: el agente EXISTE pero su sesión ya no sirve.

    Que los archivos de credenciales existan NO significa que el token valga —
    un OAuth expirado los deja en su sitio. 2026-08-21: por eso ACERO reintentó
    173 veces seguidas y quemó ~10 h planeando lo que nadie podía ejecutar. Al
    abrirse se guarda la huella de las credenciales de ESE momento; en cuanto el
    humano se re-loguea la huella cambia y el cortacircuitos se cierra SOLO."""
    try:
        _breaker_file().write_text(json.dumps({
            "at": time.time(), "fingerprint": _creds_fingerprint(),
            "error": str(error)[:300]}), encoding="utf-8")
    except Exception:  # noqa: BLE001 - el breaker jamás rompe una corrida
        pass


def agent_breaker_open() -> bool:
    """True si el agente quedó marcado como no-autenticado y las credenciales
    siguen SIN cambiar desde entonces (nadie ha vuelto a loguearse)."""
    try:
        d = json.loads(_breaker_file().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    return bool(d.get("fingerprint")) and d["fingerprint"] == _creds_fingerprint()


def agent_available(image: str = DEFAULT_AGENT_IMAGE) -> bool:
    """True only if docker, the agent image, and host Claude credentials all exist
    AND the session is not known-dead (cortacircuitos cerrado).

    Callers fall back to the pure-completion codegen path when this is False."""
    if not shutil.which("docker"):
        return False
    if agent_breaker_open():
        return False
    try:
        if subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode != 0:
            return False
        if subprocess.run(["docker", "image", "inspect", image],
                          capture_output=True, timeout=10).returncode != 0:
            return False
    except Exception:  # noqa: BLE001
        return False
    return _creds_present()


@dataclass
class AgenticResult:
    ok: bool
    code: str                      # the authored analysis.py (empty if none)
    claimed: dict | None           # RESULT_JSON the agent itself reported (untrusted)
    raw: str                       # agent's final text
    error: str = ""
    num_turns: int = 0
    cost_usd: float = 0.0
    duration_sec: float = 0.0
    timed_out: bool = False
    matches: list[str] = field(default_factory=list)


def _default_runner(cmd: list[str], timeout: int) -> tuple[str, str, int]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.stdout, proc.stderr, proc.returncode


class AgenticAuthor:
    """Runs the agent in the container to AUTHOR analysis.py. Runner injectable."""

    def __init__(self, image: str = DEFAULT_AGENT_IMAGE,
                 timeout_sec: int | None = None,
                 runner=None) -> None:
        self.image = image
        self.timeout_sec = timeout_sec or DEFAULT_AGENT_TIMEOUT
        self._runner = runner or _default_runner

    def _prepare_home(self, workdir: Path) -> Path:
        """Copy the host Claude credentials into a per-run HOME under the workdir."""
        home = workdir / ".agent_home"
        (home / ".claude").mkdir(parents=True, exist_ok=True)
        src = _host_home()
        shutil.copyfile(src / ".claude" / ".credentials.json",
                        home / ".claude" / ".credentials.json")
        shutil.copyfile(src / ".claude.json", home / ".claude.json")
        return home

    def _build_cmd(self, prompt: str, workdir: Path, home: Path) -> list[str]:
        cmd = [
            "docker", "run", "--rm", "--network=bridge",
            f"--user={os.getuid()}:{os.getgid()}",
            "--security-opt=no-new-privileges",
            "-e", "HOME=/home",
            "-v", f"{home}:/home:rw",
            "-v", f"{workdir}:/work:rw",
        ]
        # The preregistered data is mounted READ-ONLY even inside the rw /work, so
        # the agent physically cannot alter it during authoring (integrity rule).
        data_dir = workdir / "data"
        if data_dir.exists():
            cmd += ["-v", f"{data_dir}:/work/data:ro"]
        cmd += [
            "-w", "/work",
            self.image,
            "claude", "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--allowedTools", "Write", "Bash", "Read", "Edit",
            "--add-dir", "/work",
        ]
        return cmd

    @staticmethod
    def _extract_claimed(text: str) -> dict | None:
        m = list(_RESULT_RE.finditer(text or ""))
        if not m:
            return None
        try:
            return json.loads(m[-1].group(1))
        except Exception:  # noqa: BLE001
            return None

    def author(self, prompt: str, workdir: str | Path) -> AgenticResult:
        ws = Path(workdir).resolve()
        ws.mkdir(parents=True, exist_ok=True)
        home = self._prepare_home(ws)
        cmd = self._build_cmd(prompt, ws, home)

        start = time.monotonic()
        try:
            stdout, stderr, rc = self._runner(cmd, self.timeout_sec)
        except subprocess.TimeoutExpired:
            return AgenticResult(ok=False, code=self._read_script(ws), claimed=None,
                                 raw="", error="agente excedió el timeout (posible cuelgue)",
                                 duration_sec=round(time.monotonic() - start, 2),
                                 timed_out=True)
        finally:
            shutil.rmtree(home, ignore_errors=True)   # never keep credentials on disk
        dur = round(time.monotonic() - start, 2)

        env = self._parse_envelope(stdout)
        code = self._read_script(ws)
        raw = str(env.get("result", "")) if env else stdout[:2000]
        if env is None:
            return AgenticResult(ok=False, code=code, claimed=None, raw=raw,
                                 error=f"salida no-JSON del agente (rc={rc}): {stderr[:300]}",
                                 duration_sec=dur)
        if env.get("is_error"):
            return AgenticResult(ok=False, code=code, claimed=None, raw=raw,
                                 error=f"agente error: {raw[:300]}", duration_sec=dur,
                                 num_turns=int(env.get("num_turns", 0)))
        if not code.strip():
            return AgenticResult(ok=False, code="", claimed=None, raw=raw,
                                 error=f"el agente no escribió {SCRIPT_NAME}", duration_sec=dur,
                                 num_turns=int(env.get("num_turns", 0)))
        # The agent writes its final RESULT_JSON to agent_result.json (most
        # reliable); fall back to parsing its prose or the script text.
        claimed = self._read_claimed_file(ws) or self._extract_claimed(raw) \
            or self._extract_claimed(code)
        usage = env.get("total_cost_usd") or 0.0
        return AgenticResult(ok=True, code=code, claimed=claimed, raw=raw,
                             num_turns=int(env.get("num_turns", 0)),
                             cost_usd=float(usage), duration_sec=dur)

    @staticmethod
    def _read_claimed_file(ws: Path) -> dict | None:
        f = ws / "agent_result.json"
        if not f.exists():
            return None
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            return obj if isinstance(obj, dict) else None
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _read_script(ws: Path) -> str:
        f = ws / SCRIPT_NAME
        try:
            return f.read_text(encoding="utf-8") if f.exists() else ""
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _parse_envelope(stdout: str) -> dict | None:
        """claude -p --output-format json prints one JSON object (the result envelope)."""
        s = (stdout or "").strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:  # noqa: BLE001
            # tolerate leading/trailing noise: grab the last {...} block
            m = re.search(r"\{.*\}", s, re.DOTALL)
            if not m:
                return None
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                return None
