"""Restricted local runner for Python scripts.

Guarantees (subprocess backend, POSIX):
  * Static screening refuses obviously dangerous code first.
  * Execution happens in an isolated per-run workspace; the working directory is
    that workspace and writes elsewhere are discouraged by policy + cwd.
  * Environment is stripped of secrets (only a minimal allowlist passed through).
  * Network is disabled by injecting a sitecustomize that blocks socket creation.
  * CPU time and address-space (memory) are capped via the ``resource`` module.
  * A wall-clock timeout kills the process group.
  * stdout, stderr, exit code, and duration are captured.

A Docker backend is offered where available for stronger isolation; the
subprocess backend is the portable default and is what the tests exercise.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core.errors import SandboxError
from ..policies.loader import PolicyBundle, load_policies
from .screen import screen_code

# Prepended to the executed script (after the USER code passes static screening)
# to block network access at runtime. Prepending — rather than a PYTHONPATH
# sitecustomize — is required because we run with ``-I`` (isolated), which makes
# the interpreter ignore PYTHONPATH. This is defense in depth on top of screening.
_NO_NETWORK_PREAMBLE = """import socket as _s
def _acero_blocked(*a, **k):
    raise OSError("network access is disabled in the ACERO sandbox")
_s.socket = _acero_blocked
_s.create_connection = _acero_blocked
try:
    _s.socketpair = _acero_blocked
except Exception:
    pass
del _s
# --- end ACERO sandbox network guard ---
"""


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool
    workspace: str
    status: str  # ok | failed | timeout | refused
    screen_matches: list[str] = field(default_factory=list)


def _preexec(cpu_seconds: int, mem_mb: int):  # pragma: no cover - POSIX child
    """Set resource limits and a new process group in the child before exec."""
    import resource

    os.setsid()
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    mem_bytes = mem_mb * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ValueError, OSError):
        pass
    # No core dumps, cap number of processes to prevent fork bombs.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except (ValueError, OSError):
        pass


class SubprocessRunner:
    def __init__(self, bundle: PolicyBundle | None = None) -> None:
        self.bundle = bundle or load_policies()
        self.exec_policy = self.bundle.execution.get("sandbox", {})

    def run(
        self,
        code: str,
        workspace: str | Path,
        *,
        timeout_sec: int | None = None,
        memory_mb: int | None = None,
        allow_network: bool = False,
    ) -> SandboxResult:
        ws = Path(workspace)
        ws.mkdir(parents=True, exist_ok=True)

        screen = screen_code(code, self.bundle)
        if not screen.allowed:
            return SandboxResult(
                exit_code=126, stdout="", stderr=screen.reason, duration_sec=0.0,
                timed_out=False, workspace=str(ws), status="refused",
                screen_matches=screen.matches,
            )

        timeout = timeout_sec or int(self.exec_policy.get("timeout_sec", 30))
        mem = memory_mb or int(self.exec_policy.get("memory_mb", 1024))
        cpu_seconds = int(self.exec_policy.get("cpu_seconds", timeout))

        network_disabled = (
            not allow_network
            and str(self.exec_policy.get("network", "disabled")) == "disabled"
        )
        # Screening already ran on the USER code; prepend the guard afterwards so
        # its own "socket" reference does not trip the screen.
        full_code = (_NO_NETWORK_PREAMBLE + code) if network_disabled else code

        script_path = ws / "code" / "script.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(full_code, encoding="utf-8")

        # Minimal, secret-free environment (secrets are stripped: os.environ is NOT passed).
        env = {
            "PATH": "/usr/bin:/bin",
            "PYTHONHASHSEED": "0",
            "HOME": str(ws),
            "TMPDIR": str(ws),
            "LANG": "C.UTF-8",
        }

        start = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=str(ws),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=(lambda: _preexec(cpu_seconds, mem)) if os.name == "posix" else None,
            )
            exit_code = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124

            def _as_text(v: object) -> str:
                if isinstance(v, bytes):
                    return v.decode("utf-8", "replace")
                return v or "" if isinstance(v, str) else ""

            stdout = _as_text(exc.stdout)
            stderr = _as_text(exc.stderr) + "\n[ACERO sandbox] wall-clock timeout"
        except Exception as exc:  # pragma: no cover - defensive
            raise SandboxError(f"Sandbox execution failed: {exc}") from exc

        duration = time.monotonic() - start
        max_out = int(self.exec_policy.get("max_output_bytes", 5_000_000))
        stdout = stdout[:max_out]
        stderr = stderr[:max_out]
        status = "timeout" if timed_out else ("ok" if exit_code == 0 else "failed")
        return SandboxResult(
            exit_code=exit_code, stdout=stdout, stderr=stderr, duration_sec=round(duration, 4),
            timed_out=timed_out, workspace=str(ws), status=status,
        )


def get_runner(backend: str = "subprocess", bundle: PolicyBundle | None = None,
               *, strict: bool = False):
    """Factory for sandbox runners.

    ``docker`` returns the hardened Docker backend when Docker and the sandbox
    image are available. If they are not: with ``strict=True`` it raises, otherwise
    it falls back to the subprocess runner (logging the reason via the returned
    runner's type). ``subprocess`` always returns the portable subprocess runner.
    """
    if backend == "docker":
        from .docker_runner import DockerRunner, docker_available, image_present

        if docker_available() and image_present():
            return DockerRunner(bundle)
        if strict:
            from ..core.errors import SandboxError

            raise SandboxError(
                "Docker backend requested but Docker or the sandbox image is "
                "unavailable. Build it with infra/sandbox/build.sh."
            )
        return SubprocessRunner(bundle)
    return SubprocessRunner(bundle)
