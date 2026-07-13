"""Source adapters. Local ingestion is enabled; network sources are policy-gated.

The arXiv/Crossref/OpenAlex adapters are implemented as *interfaces with a guard*
per the mission: the shape exists and is tested with mocks, but real network
fetches are disabled by policy (data_access.yaml) and require human approval.
"""

from __future__ import annotations

from typing import Protocol

from ..core.errors import PolicyViolation
from ..policies.guard import PolicyGuard


class Source(Protocol):
    name: str

    def enabled(self, guard: PolicyGuard) -> bool: ...


class ArxivSource:
    """arXiv adapter. Off by default; enabling requires human approval + rate limits."""

    name = "arxiv"

    def enabled(self, guard: PolicyGuard) -> bool:
        cfg = guard.bundle.data_access.get("sources", {}).get("arxiv", {})
        return bool(cfg.get("enabled", False))

    def fetch(self, guard: PolicyGuard, query: str):  # pragma: no cover - network gated
        if not self.enabled(guard):
            raise PolicyViolation(
                "arXiv source is disabled by data_access policy; human approval required "
                "to enable network ingestion."
            )
        raise NotImplementedError(
            "Network fetch intentionally not implemented in this build (local-first). "
            "Enable in data_access.yaml and implement a rate-limited client to activate."
        )


AVAILABLE_SOURCES: dict[str, Source] = {"arxiv": ArxivSource()}
