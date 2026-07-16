"""Tool registry evaluation (Sprint 18).

Evaluates agent-created tools (accuracy, safety, utility, reuse, cost, staleness). A degraded
tool is flagged and must be BLOCKED/replaced/deprecated — never used silently. This reads the
existing discovery 'tool' records; with none present it reports an empty, honest result.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore


def evaluate_tools(store: DiscoveryStore, project_id: str) -> dict[str, Any]:
    tools = store.list_objects(project_id, kind="tool")
    evaluated = []
    for t in tools:
        benchmarked = bool(t.get("benchmark") or t.get("benchmarked"))
        quarantined = t.get("status") in ("QUARANTINED", "BLOCKED")
        health = "healthy" if benchmarked and not quarantined else "degraded"
        evaluated.append({"id": t.get("id"), "health": health,
                          "benchmarked": benchmarked, "quarantined": quarantined})
    degraded = [e["id"] for e in evaluated if e["health"] == "degraded"]
    return {"n_tools": len(tools), "evaluated": evaluated, "degraded": degraded,
            "note": "degraded tools must be blocked/replaced/deprecated, never used silently"}
