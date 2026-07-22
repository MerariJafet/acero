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

def _session_store_path():
    from ..core.config import repo_root
    return repo_root() / "acero_data" / "portal_sessions.json"


# process-level auth singletons (local single-process portal). Sessions persist to
# disk so a portal restart does NOT log the user out.
_SESSIONS = SessionManager(persist_path=_session_store_path())
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
    location: dict[str, Any] | None = None   # {scope: global|project|phase|course, ...}


class EduPlanBody(BaseModel):
    use_ai: bool = True


class CourseBody(BaseModel):
    topic_ids: list[str] | None = None
    use_ai: bool = True


class ProgressBody(BaseModel):
    lesson_key: str


class HypoBody(BaseModel):
    n: int = 6
    use_ai: bool = True
    focus: str = ""


class HypStatusBody(BaseModel):
    status: str
    reason: str = ""


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

    @r.get("/api/projects/{project_id}/phases")
    def project_phases(project_id: str, sess: Session = Depends(_require_session)
                       ) -> dict[str, Any]:
        """The 6-phase research flow view of a project (from real artifacts)."""
        from .phases import build_phases
        ph = build_phases(project_id)
        if ph is None:
            raise HTTPException(404, "project not found")
        return ph

    @r.post("/api/copilot/global")
    def global_copilot(body: CopilotBody, sess: Session = Depends(_require_session),
                       x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """General chat across ALL investigations (not tied to one project)."""
        _require_csrf(sess, x_csrf_token)
        if not body.message.strip():
            raise HTTPException(422, "message is required")
        from .copilot import ResearchCopilot
        return ResearchCopilot().chat("", body.message,
                                      location={"scope": "global"})

    @r.post("/api/projects/{project_id}/edu-plan")
    def project_edu_plan(project_id: str, body: EduPlanBody,
                         sess: Session = Depends(_require_session),
                         x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Generate an educational study plan (toggleable topics) for the project."""
        _require_csrf(sess, x_csrf_token)
        from .education import EducationService
        return EducationService().build_edu_plan(project_id, use_ai=body.use_ai)

    @r.get("/api/projects/{project_id}/edu-plan")
    def project_edu_plan_get(project_id: str, sess: Session = Depends(_require_session)
                             ) -> dict[str, Any]:
        from .education import EducationService
        plan = EducationService().latest_plan(project_id)
        return {"found": plan is not None, "plan": plan}

    @r.post("/api/projects/{project_id}/course")
    def project_course(project_id: str, body: CourseBody,
                       sess: Session = Depends(_require_session),
                       x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Generate an LMS course from the selected plan topics."""
        _require_csrf(sess, x_csrf_token)
        from .education import EducationService
        return EducationService().generate_course(project_id, topic_ids=body.topic_ids,
                                                  use_ai=body.use_ai)

    @r.get("/api/courses")
    def courses_list(sess: Session = Depends(_require_session)) -> list[dict[str, Any]]:
        from .education import EducationService
        return EducationService().list_courses()

    @r.get("/api/courses/{course_id}")
    def course_get(course_id: str, sess: Session = Depends(_require_session)
                   ) -> dict[str, Any]:
        from .education import EducationService
        c = EducationService().get_course(course_id)
        if not c:
            raise HTTPException(404, "course not found")
        return c

    @r.post("/api/courses/{course_id}/progress")
    def course_progress(course_id: str, body: ProgressBody,
                        sess: Session = Depends(_require_session),
                        x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .education import EducationService
        return EducationService().mark_lesson(course_id, body.lesson_key)

    @r.post("/api/courses/{course_id}/sync")
    def course_sync(course_id: str, sess: Session = Depends(_require_session),
                    x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Add topics for investigation angles not yet covered by the course."""
        _require_csrf(sess, x_csrf_token)
        from .education import EducationService
        return EducationService().sync_course(course_id)

    @r.post("/api/courses/{course_id}/delete")
    def course_delete(course_id: str, sess: Session = Depends(_require_session),
                      x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Delete a course (e.g. a duplicate)."""
        _require_csrf(sess, x_csrf_token)
        from .education import EducationService
        return EducationService().delete_course(course_id)

    @r.post("/api/projects/{project_id}/hypotheses/generate")
    def project_gen_hypotheses(project_id: str, body: HypoBody,
                               sess: Session = Depends(_require_session),
                               x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Generate critical + creative competing hypotheses (Codex CLI local)."""
        _require_csrf(sess, x_csrf_token)
        from .hypotheses import HypothesisService
        return HypothesisService().generate(project_id, n=body.n, use_ai=body.use_ai,
                                            focus=body.focus)

    @r.get("/api/projects/{project_id}/hypothesis/{hyp_id}")
    def project_hypothesis(project_id: str, hyp_id: str,
                           sess: Session = Depends(_require_session)) -> dict[str, Any]:
        from .hypotheses import HypothesisService
        h = HypothesisService().get(hyp_id)
        if not h:
            raise HTTPException(404, "hypothesis not found")
        return h

    # --- hypothesis-centric flow: approve → literature → experiments -------
    @r.post("/api/projects/{project_id}/hypothesis/{hyp_id}/status")
    def hyp_status(project_id: str, hyp_id: str, body: HypStatusBody,
                   sess: Session = Depends(_require_session),
                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .hypothesis_flow import HypothesisFlow
        out = HypothesisFlow().set_status(project_id, hyp_id, body.status, body.reason)
        if not out["ok"]:
            raise HTTPException(422, out["error"])
        return out

    @r.get("/api/projects/{project_id}/hyp-flow")
    def hyp_flow(project_id: str, sess: Session = Depends(_require_session)
                 ) -> dict[str, Any]:
        """Approved hypotheses with their literature/confrontation and experiments."""
        from .critic import CriticAgent
        from .hypothesis_flow import HypothesisFlow
        fl = HypothesisFlow()
        crits = CriticAgent().latest_by_target(project_id)
        out = []
        for h in fl.approved(project_id):
            exps = fl.experiments_for(project_id, h["id"])
            for e in exps:
                e["critique"] = crits.get(e.get("id", ""))
            out.append({
                "id": h["id"], "tag": h.get("tag"), "title": h.get("title", ""),
                "trigger_question": h.get("trigger_question", ""),
                "kind": h.get("kind", ""),
                "version": int(h.get("version", 1)),
                "history": h.get("history", []),
                "lit_status": h.get("lit_status", "PENDING"),
                "lit_count": h.get("lit_count", 0),
                "confrontation": h.get("confrontation"),
                "critique": crits.get(h["id"]),
                "experiments": exps,
            })
        return {"project_id": project_id, "approved": out, "n": len(out)}

    @r.post("/api/projects/{project_id}/hypothesis/{hyp_id}/investigate")
    def hyp_investigate(project_id: str, hyp_id: str,
                        sess: Session = Depends(_require_session),
                        x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .hypothesis_flow import HypothesisFlow
        return HypothesisFlow().investigate(project_id, hyp_id)

    @r.post("/api/projects/{project_id}/obsidian/sync")
    def obsidian_sync(project_id: str, sess: Session = Depends(_require_session),
                      x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Export the project's research memory to the ACERO-Research Obsidian vault."""
        _require_csrf(sess, x_csrf_token)
        from .obsidian_sync import ObsidianExporter
        return ObsidianExporter().sync_project(project_id)

    @r.post("/api/projects/{project_id}/hypothesis/{hyp_id}/adopt-improved")
    def hyp_adopt_improved(project_id: str, hyp_id: str,
                           sess: Session = Depends(_require_session),
                           x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .hypothesis_flow import HypothesisFlow
        return HypothesisFlow().adopt_improved(project_id, hyp_id)

    @r.post("/api/projects/{project_id}/investigate-all")
    def hyp_investigate_all(project_id: str, sess: Session = Depends(_require_session),
                            x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Launch PARALLEL literature subagents (one per approved hypothesis)."""
        _require_csrf(sess, x_csrf_token)
        from .parallel_runs import start_investigate_all
        return {"ok": True, "run": start_investigate_all(project_id)}

    @r.get("/api/runs/{run_id}")
    def run_status(run_id: str, sess: Session = Depends(_require_session)
                   ) -> dict[str, Any]:
        """Live progress of a parallel run (subagents per item)."""
        from .parallel_runs import get_run
        run = get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found (o el portal se reinició)")
        return run

    @r.post("/api/projects/{project_id}/hypothesis/{hyp_id}/experiments/propose")
    def hyp_propose_exps(project_id: str, hyp_id: str,
                         sess: Session = Depends(_require_session),
                         x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .hypothesis_flow import HypothesisFlow
        return HypothesisFlow().propose_experiments(project_id, hyp_id)

    @r.post("/api/projects/{project_id}/experiment/{exp_id}/run")
    def exp_run(project_id: str, exp_id: str, sess: Session = Depends(_require_session),
                x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        _require_csrf(sess, x_csrf_token)
        from .hypothesis_flow import HypothesisFlow
        return HypothesisFlow().run_experiment(project_id, exp_id)

    @r.post("/api/projects/{project_id}/experiments/run-all")
    def exp_run_all(project_id: str, sess: Session = Depends(_require_session),
                    x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Launch PARALLEL experiment subagents (one per proposed experiment)."""
        _require_csrf(sess, x_csrf_token)
        from .parallel_runs import start_run_all_experiments
        return {"ok": True, "run": start_run_all_experiments(project_id)}

    @r.get("/api/projects/{project_id}/status")
    def project_status(project_id: str, sess: Session = Depends(_require_session)
                       ) -> dict[str, Any]:
        """Narrative status: what's done, where we are, what's next, decisions."""
        from .status import build_status
        st = build_status(project_id)
        if st is None:
            raise HTTPException(404, "project not found")
        return st

    @r.get("/api/projects/{project_id}/chat")
    def project_chat(project_id: str, sess: Session = Depends(_require_session)
                     ) -> list[dict[str, Any]]:
        """Persistent copilot chat thread for the project."""
        from .copilot import ResearchCopilot
        return ResearchCopilot().get_chat(project_id)

    @r.get("/api/projects/{project_id}/learning")
    def project_learning(project_id: str, sess: Session = Depends(_require_session)
                         ) -> dict[str, Any]:
        """Learning Center scoped to THIS project (domain-matched curricula)."""
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        from ..understanding.curriculum.research_curriculum import requirements_for
        p = ResearchLedger(default_session_factory()).get_project(project_id)
        if p is None:
            raise HTTPException(404, "project not found")
        domain_map = {
            "astronomy": ["transit", "sunspots"],
            "physics": ["sindy", "reliability"],
        }
        kinds = domain_map.get(p.domain, ["reliability"])
        concepts: list[dict[str, Any]] = []
        for kind in kinds:
            for req in requirements_for(kind, project_id):
                concepts.append({
                    "curriculum": kind, "concept": req.concept,
                    "reason": req.reason_required,
                    "criticality": str(getattr(req.criticality, "value", req.criticality)),
                    "blocking": bool(req.blocking),
                })
        return {"project_id": project_id, "domain": p.domain, "curricula": kinds,
                "n_concepts": len(concepts), "concepts": concepts,
                "note": ("Estos conceptos son el contexto de aprendizaje de ESTE proyecto; "
                         "los marcados como bloqueantes deben comprenderse antes de aprobar "
                         "un dossier.")}

    @r.post("/api/projects/{project_id}/copilot")
    def project_copilot(project_id: str, body: CopilotBody,
                        sess: Session = Depends(_require_session),
                        x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Chat with the per-project Research Copilot (Codex-backed, methodology-guarded)."""
        _require_csrf(sess, x_csrf_token)
        if not body.message.strip():
            raise HTTPException(422, "message is required")
        from .copilot import ResearchCopilot
        return ResearchCopilot().chat(project_id, body.message, location=body.location)

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

    @r.post("/api/projects/{project_id}/deep-investigation")
    def project_deep_investigation(project_id: str, sess: Session = Depends(_require_session),
                                   x_csrf_token: str | None = Header(default=None)) -> dict[str, Any]:
        """Deep multi-angle investigation: real data + real literature + honest synthesis."""
        _require_csrf(sess, x_csrf_token)
        from ..studies.place_in_universe import investigate
        return investigate(project_id)

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
