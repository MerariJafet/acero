"""Reproducibility artifact bundle for an execution run.

Each run writes a standard directory a third party can re-execute and verify:
  manifest.json, environment.json, inputs/, code/, outputs/, logs/, metrics.json,
  result.md, provenance.json, checksums.txt
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.hashing import hash_file, hash_json


def capture_environment() -> dict[str, Any]:
    """Record the environment needed to reproduce a run. No secrets included."""
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "implementation": platform.python_implementation(),
        "captured_at": now_iso(),
    }


class ArtifactBundle:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        for sub in ("inputs", "code", "outputs", "logs"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def write_code(self, code: str, name: str = "script.py") -> Path:
        p = self.root / "code" / name
        p.write_text(code, encoding="utf-8")
        return p

    def write_input(self, name: str, content: str) -> Path:
        p = self.root / "inputs" / name
        p.write_text(content, encoding="utf-8")
        return p

    def write_output(self, name: str, content: str) -> Path:
        p = self.root / "outputs" / name
        p.write_text(content, encoding="utf-8")
        return p

    def write_logs(self, stdout: str, stderr: str) -> None:
        (self.root / "logs" / "stdout.txt").write_text(stdout, encoding="utf-8")
        (self.root / "logs" / "stderr.txt").write_text(stderr, encoding="utf-8")

    def write_metrics(self, metrics: dict[str, Any]) -> None:
        (self.root / "metrics.json").write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_result_md(self, text: str) -> None:
        (self.root / "result.md").write_text(text, encoding="utf-8")

    def write_manifest(self, manifest: dict[str, Any]) -> None:
        (self.root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_provenance(self, provenance: dict[str, Any]) -> None:
        (self.root / "provenance.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def write_environment(self, env: dict[str, Any]) -> None:
        (self.root / "environment.json").write_text(
            json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def checksum_all(self) -> dict[str, str]:
        """Hash every file in the bundle (except checksums.txt) and write checksums.txt."""
        sums: dict[str, str] = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and path.name != "checksums.txt":
                rel = str(path.relative_to(self.root))
                sums[rel] = hash_file(path)
        (self.root / "checksums.txt").write_text(
            "\n".join(f"{h}  {name}" for name, h in sums.items()) + "\n", encoding="utf-8"
        )
        return sums


def hash_inputs_outputs(bundle: ArtifactBundle) -> tuple[str, str, str]:
    """Return (input_hash, code_hash, output_hash) aggregated over the bundle dirs."""

    def dir_hash(sub: str) -> str:
        entries = {}
        d = bundle.root / sub
        for p in sorted(d.rglob("*")):
            if p.is_file():
                entries[str(p.relative_to(d))] = hash_file(p)
        return hash_json(entries)

    return dir_hash("inputs"), dir_hash("code"), dir_hash("outputs")
