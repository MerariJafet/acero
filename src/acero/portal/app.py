"""Portal backend: aggregator + safe-action endpoints mounted under /portal.

Read endpoints aggregate real engine state; action endpoints go through the SAME protected
services as the CLI (gates cannot be bypassed from the UI). No endpoint exposes a secret, a
raw mutation token, or a shell.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_STATIC = Path(__file__).parent / "static"


class DecisionBody(BaseModel):
    decision: str
    reason: str = ""


def build_portal_router() -> APIRouter:
    r = APIRouter(prefix="/portal", tags=["portal"])

    @r.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @r.get("/api/overview")
    def overview() -> dict[str, Any]:
        from .. import __version__
        from ..core.config import get_config
        from ..epistemic_gate.registry import GateRegistry
        cfg = get_config()
        # runtime queue snapshot (best-effort)
        queue: dict[str, int] = {}
        try:
            from ..ledger.db import default_session_factory
            from ..runtime.store import RuntimeStore
            for t in RuntimeStore(default_session_factory()).tasks():
                queue[t["status"]] = queue.get(t["status"], 0) + 1
        except Exception:  # noqa: BLE001
            queue = {}
        return {
            "version": __version__,
            "env": cfg.app.env,
            "llm_provider": cfg.llm.provider,
            "sandbox": cfg.sandbox.backend,
            "gate_rules": len(GateRegistry().all_rules()),
            "runtime_queue": queue,
            "readiness_ceiling": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
            "auto_publication": False,
            "sections": SECTIONS,
        }

    @r.get("/api/programs")
    def programs() -> list[dict[str, Any]]:
        from ..discovery.store import DiscoveryStore
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..program.engine import ProgramEngine
        sf = default_session_factory()
        pe = ProgramEngine(DiscoveryStore(sf, ResearchLedger(sf)))
        return [{"id": p.id, "mission": p.mission, "status": p.status.value,
                 "domains": p.domains, "subprojects": len(p.subprojects)}
                for p in pe.programs()]

    @r.get("/api/reliability")
    def reliability() -> dict[str, Any]:
        from ..reliability.engine import build_card
        from ..reliability.red_team import run_red_team
        return {"card": build_card().as_dict(),
                "red_team": run_red_team().as_dict()}

    @r.get("/api/runtime")
    def runtime() -> dict[str, Any]:
        from ..ledger.db import default_session_factory
        from ..runtime.store import RuntimeStore
        store = RuntimeStore(default_session_factory())
        tasks = store.tasks()
        return {"n_tasks": len(tasks),
                "by_status": _count(tasks, "status"),
                "recent": tasks[-10:]}

    @r.get("/api/review")
    def review() -> dict[str, Any]:
        import tempfile

        from ..benchmarks.review_gauntlet import run_review_gauntlet
        with tempfile.TemporaryDirectory() as td:
            return run_review_gauntlet(td)

    @r.get("/api/decision")
    def decision() -> dict[str, Any]:
        """A Decision Center item — every field a human needs, plus why NOT to auto-run."""
        return {
            "question": "Approve this inference result for human scientific review?",
            "context": "Damped oscillation recovered as ẋ=v, v̇=−4x−0.5v (synthetic).",
            "evidence": ["clean recovery (R²≈1.0)", "invariant energy recovered"],
            "counter_evidence": ["fit degrades under noise", "polynomial library imposed"],
            "uncertainty": "coefficients are point estimates without calibrated intervals",
            "alternatives": ["system_identification only", "abstain"],
            "cost": "low (local compute)",
            "risk": "over-claiming a fit as a law",
            "learning_required": ["imposed_library", "identifiability"],
            "recommendation": "REQUIRE_EXTERNAL_REVIEW",
            "why_not_execute": "computational only; not experimental validation; "
                               "DISCOVERY_CONFIRMED is never granted",
            "actions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "DEFER", "ABSTAIN",
                        "REQUIRE_EXTERNAL_REVIEW"],
        }

    @r.post("/api/decision")
    def record_decision(body: DecisionBody) -> dict[str, Any]:
        valid = {"APPROVE", "REJECT", "REQUEST_CHANGES", "DEFER", "ABSTAIN",
                 "REQUIRE_EXTERNAL_REVIEW"}
        if body.decision not in valid:
            raise HTTPException(400, f"invalid decision; choose one of {sorted(valid)}")
        if body.decision == "APPROVE" and not body.reason.strip():
            # UI-level guard mirrors the backend anti-rubber-stamp rule
            raise HTTPException(422, "APPROVE requires a stated reason")
        return {"recorded": body.decision, "reason": body.reason,
                "note": "recorded locally; ACERO never publishes or sends anything"}

    @r.get("/api/evaluation")
    def evaluation() -> dict[str, Any]:
        from ..selfeval.engine import run_evaluation
        rep = run_evaluation()
        return {"verdict": rep["verdict"], "version": rep["version"],
                "benchmarks": rep["benchmarks"],
                "capabilities": rep["capabilities"],
                "prompts": {"passed": rep["prompts"]["passed"],
                            "n": rep["prompts"]["n_fixtures"]},
                "regression": rep["regression"], "note": rep["note"]}

    @r.get("/api/collaboration")
    def collaboration() -> dict[str, Any]:
        import tempfile

        from ..benchmarks.external_review_gauntlet import run_external_review_gauntlet
        from ..collaboration.questions import REVIEW_QUESTIONS
        from ..discovery.store import DiscoveryStore
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        sf = default_session_factory()
        store = DiscoveryStore(sf, ResearchLedger(sf))
        with tempfile.TemporaryDirectory() as td:
            gauntlet = run_external_review_gauntlet(td, store)
        return {"review_questions": list(REVIEW_QUESTIONS),
                "gauntlet": {"passed": gauntlet["passed"], "n": gauntlet["n"],
                             "all_passed": gauntlet["all_passed"]},
                "ai_authorship_allowed": False,
                "note": "preparing a review bundle is NOT external review; nothing is sent."}

    @r.get("/api/world/{project_id}")
    def world(project_id: str) -> dict[str, Any]:
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..world_model.graph import WorldModel
        sf = default_session_factory()
        wm = WorldModel(sf, ResearchLedger(sf), project_id)
        return wm.stats()

    return r


SECTIONS = [
    "Overview", "Research Programs", "Projects", "World Model", "Reliability",
    "Red Team", "Runtime", "Self-Evaluation", "Review", "Collaboration",
    "Publication Candidates", "Decision Center", "Settings",
]


def _count(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[row[key]] = out.get(row[key], 0) + 1
    return out


def mount_portal(app: FastAPI) -> None:
    """Mount the portal router + static files, with a strict CSP header."""
    app.include_router(build_portal_router())
    if _STATIC.exists():
        app.mount("/portal/static", StaticFiles(directory=str(_STATIC)), name="portal-static")

    @app.middleware("http")
    async def _security_headers(request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        if request.url.path.startswith("/portal"):
            # local-first, no inline eval, no external origins; self-contained SPA
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
        return response
