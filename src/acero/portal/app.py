"""Portal backend: authenticated aggregator + safe-action endpoints under /portal.

Read endpoints aggregate real engine state; action endpoints go through the SAME
protected services as the CLI (gates cannot be bypassed from the UI). All ``/api``
endpoints except login/session require a valid session; mutating endpoints also
require a matching CSRF token. No endpoint exposes a secret, a raw mutation token,
or a shell.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import Response as RawResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import RateLimiter, Session, SessionManager, UserStore

_STATIC = Path(__file__).parent / "static"
_COOKIE = "acero_session"

# process-level auth singletons (local single-process portal)
_SESSIONS = SessionManager()
_LIMITER = RateLimiter()


def _user_store() -> UserStore:
    # fresh each call so ACERO_PORTAL_USERS (env) is honored at request time
    return UserStore()


class DecisionBody(BaseModel):
    decision: str
    reason: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


class ProgramBody(BaseModel):
    mission: str
    domains: list[str] = []


class ProjectBody(BaseModel):
    title: str
    domain: str = "general"
    program_id: str | None = None


class QuestionBody(BaseModel):
    program_id: str
    text: str


class HypothesesBody(BaseModel):
    project_id: str
    question: str


class ApproveBody(BaseModel):
    hypothesis_id: str
    reason: str


class ExperimentBody(BaseModel):
    project_id: str
    hypothesis_id: str


class GateBody(BaseModel):
    artifact: dict[str, Any] = {}


class WorldUpdateBody(BaseModel):
    project_id: str
    label: str


class DossierBody(BaseModel):
    project_id: str
    claim: str


class CopilotBody(BaseModel):
    message: str


class RunCycleBody(BaseModel):
    question: str


def _cookie_secure() -> bool:
    return os.environ.get("ACERO_PORTAL_COOKIE_SECURE", "0") == "1"


def _require_session(acero_session: str | None = Cookie(default=None)) -> Session:
    sess = _SESSIONS.get(acero_session)
    if sess is None:
        raise HTTPException(401, "authentication required")
    return sess


def _require_csrf(sess: Session, x_csrf_token: str | None) -> None:
    if not x_csrf_token or x_csrf_token != sess.csrf:
        raise HTTPException(403, "missing or invalid CSRF token")


def build_portal_router() -> APIRouter:
    r = APIRouter(prefix="/portal", tags=["portal"])

    # --- shell (public) ---------------------------------------------------
    @r.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    # --- auth (public) ----------------------------------------------------
    @r.post("/api/login")
    def login(body: LoginBody, response: Response, request: Request) -> dict[str, Any]:
        key = body.username or (request.client.host if request.client else "anon")
        if not _LIMITER.check(key):
            raise HTTPException(429, f"too many attempts; retry after "
                                     f"{_LIMITER.retry_after(key)}s")
        if not _user_store().verify(body.username, body.password):
            _LIMITER.record_failure(key)
            raise HTTPException(401, "invalid credentials")
        _LIMITER.record_success(key)
        sess = _SESSIONS.create(body.username)
        response.set_cookie(_COOKIE, sess.sid, httponly=True, samesite="strict",
                            secure=_cookie_secure(), max_age=int(_SESSIONS.ttl_s), path="/portal")
        return {"user": sess.user, "csrf": sess.csrf}

    @r.post("/api/logout")
    def logout(response: Response, sess: Session = Depends(_require_session),
               x_csrf_token: str | None = Header(default=None),
               acero_session: str | None = Cookie(default=None)) -> dict[str, Any]:
        # logout is state-changing: require a valid session + CSRF (Codex finding #7)
        _require_csrf(sess, x_csrf_token)
        _SESSIONS.invalidate(acero_session)
        response.delete_cookie(_COOKIE, path="/portal")
        return {"logged_out": True}

    @r.get("/api/session")
    def session_info(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        return {"user": sess.user, "csrf": sess.csrf}

    # --- reads (auth required) -------------------------------------------
    @r.get("/api/overview")
    def overview(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from .. import __version__
        from ..core.config import get_config
        from ..epistemic_gate.registry import GateRegistry
        cfg = get_config()
        queue: dict[str, int] = {}
        try:
            from ..ledger.db import default_session_factory
            from ..runtime.store import RuntimeStore
            for t in RuntimeStore(default_session_factory()).tasks():
                queue[t["status"]] = queue.get(t["status"], 0) + 1
        except Exception:  # noqa: BLE001
            queue = {}
        return {
            "version": __version__, "env": cfg.app.env, "user": sess.user,
            "llm_provider": cfg.llm.provider, "sandbox": cfg.sandbox.backend,
            "gate_rules": len(GateRegistry().all_rules()), "runtime_queue": queue,
            "readiness_ceiling": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
            "auto_publication": False, "sections": SECTIONS,
        }

    @r.get("/api/projects")
    def projects_list(sess: Session = Depends(_require_session)) -> list[dict[str, Any]]:
        """Every research project with a live status/progress summary."""
        from ..discovery.store import DiscoveryStore
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..world_model.graph import WorldModel
        sf = default_session_factory()
        lg = ResearchLedger(sf)
        store = DiscoveryStore(sf, lg)
        out: list[dict[str, Any]] = []
        for p in lg.list_projects():
            ev = lg.provenance_for_project(p.id)
            hyps = store.list_objects(p.id, kind="candidate")
            exps = store.list_objects(p.id, kind="experiment")
            negs = store.list_objects(p.id, kind="negative")
            wm = WorldModel(sf, lg, p.id).stats()
            n_nodes = int(wm.get("n_nodes", 0))
            last = max((str(e.get("at") or e.get("timestamp") or "") for e in ev), default="")
            work = len(hyps) + len(exps) + n_nodes
            out.append({
                "id": p.id, "title": p.title, "domain": p.domain, "state": p.state.value,
                "created_at": p.created_at, "hypotheses": len(hyps),
                "experiments": len(exps), "negatives": len(negs), "world_nodes": n_nodes,
                "events": len(ev), "last_activity": last[:19],
                "status": "empty (created, no work yet)" if work == 0 else "in progress",
            })
        out.sort(key=lambda x: x["last_activity"], reverse=True)
        return out

    @r.get("/api/projects/{project_id}")
    def project_detail(project_id: str, sess: Session = Depends(_require_session)
                       ) -> dict[str, Any]:
        """Full status + history for one project (progress, artifacts, events)."""
        from ..discovery.store import DiscoveryStore
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..world_model.graph import WorldModel
        sf = default_session_factory()
        lg = ResearchLedger(sf)
        p = lg.get_project(project_id)
        if p is None:
            raise HTTPException(404, "project not found")
        store = DiscoveryStore(sf, lg)
        ev = lg.provenance_for_project(project_id)
        hist = [{"at": str(e.get("at") or e.get("timestamp") or "")[:19],
                 "action": e.get("action"), "actor": e.get("actor"),
                 "summary": (e.get("summary") or "")[:120]} for e in ev]
        hist.sort(key=lambda h: str(h["at"]), reverse=True)
        return {
            "id": p.id, "title": p.title, "domain": p.domain, "state": p.state.value,
            "created_at": p.created_at,
            "hypotheses": store.list_objects(project_id, kind="candidate"),
            "experiments": store.list_objects(project_id, kind="experiment"),
            "negatives": store.list_objects(project_id, kind="negative"),
            "world": WorldModel(sf, lg, project_id).stats(),
            "history": hist,
        }

    @r.post("/api/projects/{project_id}/copilot")
    def project_copilot(project_id: str, body: CopilotBody,
                        sess: Session = Depends(_require_session),
                        x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Chat with the per-project Research Copilot (Codex-backed, methodology-guarded)."""
        _require_csrf(sess, x_csrf_token)
        if not body.message.strip():
            raise HTTPException(422, "message is required")
        from .copilot import ResearchCopilot
        return ResearchCopilot().chat(project_id, body.message)

    @r.post("/api/projects/{project_id}/run-cycle")
    def project_run_cycle(project_id: str, body: RunCycleBody,
                          sess: Session = Depends(_require_session),
                          x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Execute one REAL ACERO research cycle on the project (gate-guarded)."""
        _require_csrf(sess, x_csrf_token)
        if not body.question.strip():
            raise HTTPException(422, "question is required")
        from .copilot import run_research_cycle
        return run_research_cycle(project_id, body.question)

    @r.post("/api/projects/{project_id}/verify-real-data")
    def project_verify_real_data(project_id: str, sess: Session = Depends(_require_session),
                                 x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Run a REAL data-backed verification (Kepler's 3rd law on public NASA data)."""
        _require_csrf(sess, x_csrf_token)
        from .copilot import run_real_data_verification
        return run_real_data_verification(project_id)

    @r.get("/api/mesh/search")
    def mesh_search(q: str, rows: int = 5, sess: Session = Depends(_require_session)
                    ) -> dict[str, Any]:
        """Real literature search via the Scientific Knowledge Mesh (Crossref)."""
        if not q.strip():
            raise HTTPException(422, "q is required")
        from ..knowledge_mesh import mesh
        try:
            return mesh.search(q, rows=max(1, min(rows, 15)))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"mesh search error: {exc}") from exc

    @r.get("/api/mesh/sources")
    def mesh_sources(sess: Session = Depends(_require_session)) -> list[dict[str, Any]]:
        from ..knowledge_mesh import mesh
        return mesh.list_sources()

    @r.get("/api/programs")
    def programs(sess: Session = Depends(_require_session)) -> list[dict[str, Any]]:
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
    def reliability(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from ..reliability.engine import build_card
        from ..reliability.red_team import run_red_team
        return {"card": build_card().as_dict(), "red_team": run_red_team().as_dict()}

    @r.get("/api/runtime")
    def runtime(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from ..ledger.db import default_session_factory
        from ..runtime.observability import metrics_snapshot
        from ..runtime.store import RuntimeStore
        store = RuntimeStore(default_session_factory())
        tasks = store.tasks()
        return {"n_tasks": len(tasks), "by_status": _count(tasks, "status"),
                "metrics": metrics_snapshot(store), "recent": _redact_tasks(tasks[-10:])}

    @r.get("/api/metrics")
    def metrics(sess: Session = Depends(_require_session)) -> RawResponse:
        from ..ledger.db import default_session_factory
        from ..runtime.observability import prometheus_text
        from ..runtime.store import RuntimeStore
        return RawResponse(prometheus_text(RuntimeStore(default_session_factory())),
                           media_type="text/plain")

    @r.get("/api/review")
    def review(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        import tempfile

        from ..benchmarks.review_gauntlet import run_review_gauntlet
        with tempfile.TemporaryDirectory() as td:
            return run_review_gauntlet(td)

    @r.get("/api/results/cards")
    def result_cards(sess: Session = Depends(_require_session)) -> list[dict[str, Any]]:
        """Scientific result cards with full epistemic metadata (no over-claiming)."""
        return RESULT_CARDS

    @r.get("/api/learning")
    def learning(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from ..understanding.curriculum.research_curriculum import CURRICULA
        return {"curricula": sorted(CURRICULA.keys()),
                "note": "human must demonstrate understanding before a dossier is approved"}

    @r.get("/api/decision")
    def decision(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        return {
            "question": "Approve this inference result for human scientific review?",
            "context": "Damped oscillation recovered as ẋ=v, v̇=−4x−0.5v (synthetic).",
            "evidence": ["clean recovery (R²≈1.0)", "invariant energy recovered"],
            "counter_evidence": ["fit degrades under noise", "polynomial library imposed"],
            "uncertainty": "coefficients are point estimates without calibrated intervals",
            "alternatives": ["system_identification only", "abstain"],
            "cost": "low (local compute)", "risk": "over-claiming a fit as a law",
            "learning_required": ["imposed_library", "identifiability"],
            "recommendation": "REQUIRE_EXTERNAL_REVIEW",
            "why_not_execute": "computational only; not experimental validation; "
                               "DISCOVERY_CONFIRMED is never granted",
            "actions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "DEFER", "ABSTAIN",
                        "REQUIRE_EXTERNAL_REVIEW"],
        }

    @r.post("/api/decision")
    def record_decision(body: DecisionBody, sess: Session = Depends(_require_session),
                        x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        valid = {"APPROVE", "REJECT", "REQUEST_CHANGES", "DEFER", "ABSTAIN",
                 "REQUIRE_EXTERNAL_REVIEW"}
        if body.decision not in valid:
            raise HTTPException(400, f"invalid decision; choose one of {sorted(valid)}")
        if body.decision == "APPROVE" and not body.reason.strip():
            raise HTTPException(422, "APPROVE requires a stated reason")
        return {"recorded": body.decision, "reason": body.reason, "by": sess.user,
                "note": "recorded locally; ACERO never publishes or sends anything"}

    @r.get("/api/evaluation")
    def evaluation(sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from ..selfeval.engine import run_evaluation
        rep = run_evaluation()
        return {"verdict": rep["verdict"], "version": rep["version"],
                "benchmarks": rep["benchmarks"], "capabilities": rep["capabilities"],
                "prompts": {"passed": rep["prompts"]["passed"], "n": rep["prompts"]["n_fixtures"]},
                "regression": rep["regression"], "note": rep["note"]}

    @r.get("/api/collaboration")
    def collaboration(sess: Session = Depends(_require_session)) -> dict[str, Any]:
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
    def world(project_id: str, sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..world_model.graph import WorldModel
        sf = default_session_factory()
        return WorldModel(sf, ResearchLedger(sf), project_id).stats()

    @r.get("/api/world/{project_id}/nodes")
    def world_nodes(project_id: str, offset: int = 0, limit: int = 50,
                    search: str | None = None, type: str | None = None,
                    sess: Session = Depends(_require_session)) -> dict[str, Any]:
        """Paginated World Model explorer — never loads the full graph."""
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..world_model.graph import WorldModel
        from ..world_model.nodes import NodeType
        ntype = None
        if type:
            try:
                ntype = NodeType(type)
            except ValueError as exc:
                raise HTTPException(400, f"unknown node type '{type}'") from exc
        sf = default_session_factory()
        wm = WorldModel(sf, ResearchLedger(sf), project_id)
        return wm.page_nodes(offset=offset, limit=limit, ntype=ntype, search=search)

    # --- workspace actions (auth + CSRF) ----------------------------------
    def _ws() -> Any:
        from .workspace import WorkspaceService
        return WorkspaceService()

    @r.post("/api/workspace/program")
    def ws_program(body: ProgramBody, sess: Session = Depends(_require_session),
                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        if not body.mission.strip():
            raise HTTPException(422, "mission is required")
        return _ws().create_program(body.mission, body.domains)

    @r.post("/api/workspace/project")
    def ws_project(body: ProjectBody, sess: Session = Depends(_require_session),
                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        if not body.title.strip():
            raise HTTPException(422, "title is required")
        return _ws().create_project(body.title, domain=body.domain, program_id=body.program_id)

    @r.post("/api/workspace/question")
    def ws_question(body: QuestionBody, sess: Session = Depends(_require_session),
                    x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        if not body.text.strip():
            raise HTTPException(422, "question text is required")
        return _ws().add_question(body.program_id, body.text)

    @r.post("/api/workspace/hypotheses")
    def ws_hypotheses(body: HypothesesBody, sess: Session = Depends(_require_session),
                      x_csrf_token: str | None = Header(default=None)) -> list[dict[str, Any]]:
        _require_csrf(sess, x_csrf_token)
        return _ws().generate_hypotheses(body.project_id, body.question)

    @r.post("/api/workspace/approve")
    def ws_approve(body: ApproveBody, sess: Session = Depends(_require_session),
                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        try:
            return _ws().approve_hypothesis(body.hypothesis_id, body.reason)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @r.post("/api/workspace/experiment")
    def ws_experiment(body: ExperimentBody, sess: Session = Depends(_require_session),
                      x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        return _ws().run_experiment(body.project_id, body.hypothesis_id)

    @r.post("/api/workspace/gate")
    def ws_gate(body: GateBody, sess: Session = Depends(_require_session),
                x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        return _ws().gate_check(body.artifact)

    @r.post("/api/workspace/world-update")
    def ws_world(body: WorldUpdateBody, sess: Session = Depends(_require_session),
                 x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        return _ws().update_world_model(body.project_id, body.label)

    @r.post("/api/workspace/dossier")
    def ws_dossier(body: DossierBody, sess: Session = Depends(_require_session),
                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        return _ws().dossier(body.project_id, body.claim)

    return r


SECTIONS = [
    "Overview", "Research Workspace", "Research Programs", "Projects", "World Model",
    "Reliability", "Red Team", "Runtime", "Self-Evaluation", "Review", "Collaboration",
    "Publication Candidates", "Decision Center", "Learning Center", "Settings",
]

# Representative scientific result cards (epistemic metadata; never over-claimed).
RESULT_CARDS = [
    {
        "title": "Damped oscillation structure recovered (synthetic)",
        "result_type": "computational_inference", "epistemic_level": "MODEL_CONSISTENT",
        "source": "inference engine (synthetic data)", "date": "2026-07-18",
        "version": "2.1.0-rc1-dev", "evidence": ["clean recovery R²≈1.0", "energy invariant"],
        "counter_evidence": ["degrades under noise", "polynomial library imposed"],
        "calibration": "point estimates, no calibrated intervals",
        "reproducibility": "deterministic (seeded)", "gate": "INFERENCE passed",
        "domain": "dynamical systems", "limitations": ["synthetic only", "not experimental"],
        "allowed_claims": ["structure consistent with a damped oscillator on this data"],
        "prohibited_claims": ["discovered a law", "confirmed a physical mechanism"],
    },
    {
        "title": "Solar cycle ~11.2 yr periodicity (SILSO, real data)",
        "result_type": "timeseries_periodicity", "epistemic_level": "OBSERVED_PATTERN",
        "source": "SILSO monthly sunspot number", "date": "2026-07-13",
        "version": "sprint-17", "evidence": ["FFT peak 11.19 yr", "bootstrap CI [10.27,11.67]"],
        "counter_evidence": ["red-noise surrogates reduce significance", "cycle length varies"],
        "calibration": "AR(1) surrogate significance", "reproducibility": "reproducible from CSV",
        "gate": "honesty gate blocks discovery claim", "domain": "heliophysics",
        "limitations": ["known phenomenon, not novel", "single record"],
        "allowed_claims": ["a ~11 yr periodicity is present in this record"],
        "prohibited_claims": ["discovered the solar cycle", "predicts future cycles"],
    },
]


def _redact_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip anything token/secret-shaped from task rows before exposing them."""
    out = []
    for t in tasks:
        out.append({k: v for k, v in t.items()
                    if k.lower() not in {"token", "signature", "secret", "hmac"}})
    return out


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
        try:
            response = await call_next(request)
        except HTTPException as exc:  # pragma: no cover - defensive
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if request.url.path.startswith("/portal"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            # local-first portal: never let the browser serve stale JS/CSS/HTML
            if request.url.path.startswith("/portal/static") or request.url.path == "/portal/":
                response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response
