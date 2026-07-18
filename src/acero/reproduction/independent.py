"""Independent-process reproduction state (Sprint 25 §25.2).

The maximum epistemic state a same-author, same-data local reproduction can reach
is INDEPENDENT_PROCESS_REPRODUCTION. It is explicitly NOT external scientific
replication, which requires independent people, independent data, and independent
instruments. This module encodes that ceiling so nothing in ACERO can label a
local re-run as external replication.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_STATE = "INDEPENDENT_PROCESS_REPRODUCTION"
FORBIDDEN_STATE = "EXTERNAL_SCIENTIFIC_REPLICATION"


@dataclass
class ReproductionRecord:
    package: str
    fresh_container: bool
    fresh_database: bool
    fresh_workspace: bool
    empty_caches: bool
    no_acero_imports: bool
    outputs: dict[str, Any]
    hash_drift: list[str]
    warnings: list[str]

    @property
    def state(self) -> str:
        # Even if everything is clean, the ceiling is process reproduction.
        return MAX_STATE

    def as_dict(self) -> dict[str, Any]:
        return {
            "package": self.package, "state": self.state,
            "is_external_replication": False,
            "fresh_container": self.fresh_container, "fresh_database": self.fresh_database,
            "fresh_workspace": self.fresh_workspace, "empty_caches": self.empty_caches,
            "no_acero_imports": self.no_acero_imports,
            "outputs": self.outputs, "hash_drift": self.hash_drift,
            "no_hash_drift": len(self.hash_drift) == 0, "warnings": self.warnings,
            "note": ("Reproduced in a separate local process; NOT external replication "
                     "(same author, same data, same methods family)."),
        }


def package_is_standalone(package_dir: Path) -> dict[str, Any]:
    """Static check: the package must not import ACERO anywhere."""
    offenders: list[str] = []
    for py in package_dir.rglob("*.py"):
        text = py.read_text()
        if "import acero" in text or "from acero" in text:
            offenders.append(py.name)
    return {"standalone": not offenders, "offenders": offenders,
            "checked": [p.name for p in package_dir.rglob("*.py")]}
