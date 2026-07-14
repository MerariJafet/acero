"""Controlled scientific-tool creation pipeline (Sprint 7.6).

Codex (or a mock) may PROPOSE a new tool, but a generated tool cannot be used in a
conclusion until it passes every gate:

    proposal -> static screen -> sandbox unit+benchmark run -> all cases pass
             -> security screen -> approval -> tool registry

Nothing runs outside the sandbox. Provenance (prompt, provider, model, code, tests,
limitations) is recorded. Unapproved tools are quarantined, never used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..provenance.events import ProvenanceAction
from ..sandbox.runner import SubprocessRunner
from ..sandbox.screen import screen_code
from .store import DiscoveryStore

# Extra tool-specific screening on top of the execution policy: block filesystem
# traversal and sensitive paths even before sandboxing.
_TRAVERSAL = re.compile(r"\.\.[\\/]|/etc/|/proc/|/sys/|~\/")


@dataclass
class ToolProposal:
    name: str
    rationale: str
    code: str                       # defines the tool function(s)
    self_test: str                  # prints JSON {"passed": int, "total": int}
    provider: str = "mock"
    model: str = "mock-1"
    prompt_version: str = "v1"
    limitations: str = ""


@dataclass
class ToolEvaluation:
    approved: bool
    stages: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"approved": self.approved, "stages": self.stages}


def screen_tool_code(code: str) -> tuple[bool, list[str]]:
    base = screen_code(code)
    matches = list(base.matches)
    if _TRAVERSAL.search(code):
        matches.append("path_traversal")
    return (not matches), matches


def evaluate_tool(proposal: ToolProposal, *, runner: SubprocessRunner | None = None,
                  workspace: str | None = None) -> ToolEvaluation:
    import tempfile

    runner = runner or SubprocessRunner()
    stages: dict[str, Any] = {}

    # Stage 1: static screen (mandatory).
    combined = proposal.code + "\n\n" + proposal.self_test
    ok_screen, matches = screen_tool_code(combined)
    stages["static_screen"] = {"ok": ok_screen, "matches": matches}
    if not ok_screen:
        return ToolEvaluation(approved=False, stages=stages)

    # Stage 2: benchmark presence (no benchmark -> not approvable).
    if "passed" not in proposal.self_test or "total" not in proposal.self_test:
        stages["benchmark_present"] = {"ok": False,
                                       "reason": "self_test must report passed/total"}
        return ToolEvaluation(approved=False, stages=stages)
    stages["benchmark_present"] = {"ok": True}

    # Stage 3: sandbox execution of code + self-test (mandatory).
    ws = workspace or tempfile.mkdtemp(prefix="acero_tool_")
    sres = runner.run(combined, ws, timeout_sec=30)
    stages["sandbox"] = {"status": sres.status, "exit_code": sres.exit_code,
                         "stderr_tail": sres.stderr.strip().splitlines()[-1:] }
    if sres.status != "ok":
        return ToolEvaluation(approved=False, stages=stages)

    # Stage 4: parse benchmark result.
    import json
    passed = total = 0
    for line in reversed(sres.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                passed, total = int(obj.get("passed", 0)), int(obj.get("total", 0))
                break
            except (json.JSONDecodeError, ValueError):
                continue
    all_pass = total > 0 and passed == total
    stages["benchmark"] = {"passed": passed, "total": total, "all_passed": all_pass}

    return ToolEvaluation(approved=all_pass, stages=stages)


class ToolRegistry:
    """Persists proposed/approved tools with full provenance. Only APPROVED tools
    may be used in conclusions."""

    def __init__(self, store: DiscoveryStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id

    def register(self, proposal: ToolProposal, evaluation: ToolEvaluation) -> dict[str, Any]:
        tool_id = new_id("tool")
        status = "APPROVED" if evaluation.approved else "QUARANTINED"
        payload = {
            "id": tool_id, "name": proposal.name, "rationale": proposal.rationale,
            "code": proposal.code, "self_test": proposal.self_test,
            "status": status, "version": 1,
            "human_author_required": True,  # a human authorises real use
            "provenance": {
                "provider": proposal.provider, "model": proposal.model,
                "prompt_version": proposal.prompt_version, "created_at": now_iso(),
            },
            "evaluation": evaluation.as_dict(),
            "limitations": proposal.limitations,
        }
        self.store.put(
            self.project_id, "tool", tool_id, payload, status=status,
            action=ProvenanceAction.TOOL_APPROVAL if evaluation.approved else ProvenanceAction.TOOL_PROPOSAL,
            summary=f"tool '{proposal.name}' -> {status}",
        )
        return payload

    def approved_tools(self) -> list[dict[str, Any]]:
        return self.store.list_objects(self.project_id, kind="tool", status="APPROVED")

    def is_usable(self, tool_id: str) -> bool:
        t = self.store.get(tool_id)
        return t is not None and t.get("status") == "APPROVED"
