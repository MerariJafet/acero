"""Docker sandbox backend — strong isolation for untrusted experiment code.

Hardening applied to every run:
  * ``--network=none``        : no network at the kernel level (not just a guard).
  * ``--read-only``           : read-only root filesystem; only the bind-mounted
                                run workspace (/work) and a small tmpfs /tmp are writable.
  * ``--cap-drop=ALL``        : drop all Linux capabilities.
  * ``--security-opt=no-new-privileges`` : no privilege escalation.
  * ``--pids-limit``          : cap process count (anti fork-bomb).
  * ``--memory`` / ``--cpus`` : hard resource limits.
  * ``--user <host uid:gid>`` : run as a non-root user that can write the bind mount.
  * No host environment is passed in, so secrets are absent by construction.
  * Static screening still runs first (defense in depth).

Requires the image built from infra/sandbox/Dockerfile (default tag
``acero-sandbox:py312``, includes numpy). Falls back with a clear error if Docker
or the image is unavailable; callers may then choose the subprocess backend.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from ..policies.loader import PolicyBundle, load_policies
from .runner import SandboxResult
from .screen import screen_code

DEFAULT_IMAGE = os.environ.get("ACERO_SANDBOX_IMAGE", "acero-sandbox:py312")


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def image_present(image: str = DEFAULT_IMAGE) -> bool:
    try:
        r = subprocess.run(["docker", "image", "inspect", image],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


class DockerRunner:
    def __init__(self, bundle: PolicyBundle | None = None, image: str = DEFAULT_IMAGE) -> None:
        self.bundle = bundle or load_policies()
        self.exec_policy = self.bundle.execution.get("sandbox", {})
        self.image = image

    def _container_name(self, workspace: Path) -> str:
        base = re.sub(r"[^a-zA-Z0-9_.-]", "_", workspace.name)[:40]
        return f"acero_sbx_{base}"

    def run(
        self,
        code: str,
        workspace: str | Path,
        *,
        timeout_sec: int | None = None,
        memory_mb: int | None = None,
        allow_network: bool = False,
    ) -> SandboxResult:
        ws = Path(workspace).resolve()
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
        cpus = str(self.exec_policy.get("cpus", 1))
        pids = str(self.exec_policy.get("pids_limit", 128))

        (ws / "code").mkdir(parents=True, exist_ok=True)
        (ws / "code" / "script.py").write_text(code, encoding="utf-8")

        name = self._container_name(ws)
        network = "none" if not allow_network else "bridge"
        cmd = [
            "docker", "run", "--rm", "--name", name,
            f"--network={network}",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=64m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--pids-limit={pids}",
            f"--memory={mem}m", f"--memory-swap={mem}m",
            f"--cpus={cpus}",
            f"--user={os.getuid()}:{os.getgid()}",
            "-e", "HOME=/tmp", "-e", "PYTHONHASHSEED=0",
            "-v", f"{ws}:/work:rw",
            "-w", "/work",
            self.image,
            "python", "-I", "code/script.py",
        ]

        start = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            exit_code = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            stdout = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout) or ""
            stderr = ((exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr) or "") \
                + "\n[ACERO docker sandbox] wall-clock timeout"

        duration = time.monotonic() - start
        max_out = int(self.exec_policy.get("max_output_bytes", 5_000_000))
        stdout = stdout[:max_out]
        stderr = stderr[:max_out]
        status = "timeout" if timed_out else ("ok" if exit_code == 0 else "failed")
        return SandboxResult(
            exit_code=exit_code, stdout=stdout, stderr=stderr,
            duration_sec=round(duration, 4), timed_out=timed_out,
            workspace=str(ws), status=status,
        )
