"""Load and validate ACERO policy files.

Policies live in ``policies/*.yaml`` and are version-controlled. They are loaded
from disk (never hard-coded) so governance changes are auditable via git.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..core.config import repo_root
from ..core.errors import ConfigError

REQUIRED_POLICIES = (
    "autonomy",
    "costs",
    "data_access",
    "execution",
    "publication",
    "research_safety",
)


@dataclass(frozen=True)
class PolicyBundle:
    """All loaded policies, keyed by name."""

    policies: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get(self, name: str) -> dict[str, Any]:
        if name not in self.policies:
            raise ConfigError(f"Policy '{name}' not loaded")
        return self.policies[name]

    @property
    def costs(self) -> dict[str, Any]:
        return self.get("costs")

    @property
    def autonomy(self) -> dict[str, Any]:
        return self.get("autonomy")

    @property
    def execution(self) -> dict[str, Any]:
        return self.get("execution")

    @property
    def research_safety(self) -> dict[str, Any]:
        return self.get("research_safety")

    @property
    def data_access(self) -> dict[str, Any]:
        return self.get("data_access")

    @property
    def publication(self) -> dict[str, Any]:
        return self.get("publication")


def load_policies(policies_dir: str | Path | None = None) -> PolicyBundle:
    root = repo_root()
    pdir = Path(policies_dir) if policies_dir else root / "policies"
    if not pdir.is_absolute():
        pdir = root / pdir
    loaded: dict[str, dict[str, Any]] = {}
    missing = []
    for name in REQUIRED_POLICIES:
        path = pdir / f"{name}.yaml"
        if not path.exists():
            missing.append(name)
            continue
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if data.get("policy") != name:
            raise ConfigError(
                f"Policy file {path.name} declares policy='{data.get('policy')}', expected '{name}'"
            )
        loaded[name] = data
    if missing:
        raise ConfigError(f"Missing required policy files: {', '.join(missing)} in {pdir}")
    return PolicyBundle(policies=loaded)
