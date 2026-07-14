"""ACERO HTTP API (FastAPI).

Minimal by design (Sprint 1/2): health, version, policies, and read-only project
access. Write operations go through the ledger service so integrity rules always apply.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .. import __version__
from ..core.config import get_config
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger
from ..policies.loader import load_policies


class ProjectCreate(BaseModel):
    title: str
    description: str = ""
    domain: str = "general"


def create_app() -> FastAPI:
    app = FastAPI(title="ACERO API", version=__version__)
    session_factory = default_session_factory()
    ledger = ResearchLedger(session_factory)

    @app.get("/health")
    def health() -> dict:
        cfg = get_config()
        return {
            "status": "ok",
            "version": __version__,
            "env": cfg.app.env,
            "llm_provider": cfg.llm.provider,
            "sandbox": cfg.sandbox.backend,
        }

    @app.get("/version")
    def version() -> dict:
        return {"version": __version__}

    @app.get("/domains")
    def domains() -> list[dict]:
        from ..domains.registry import all_plugins

        return [p.info() for p in all_plugins()]

    @app.get("/domains/{name}/benchmark")
    def domain_benchmark(name: str) -> dict:
        from ..domains.registry import get_plugin

        try:
            return get_plugin(name).benchmark().to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/policies")
    def policies() -> dict:
        bundle = load_policies()
        # Return names + versions only; never leak full internals unnecessarily.
        return {
            name: {"version": data.get("version")}
            for name, data in sorted(bundle.policies.items())
        }

    @app.get("/projects")
    def list_projects() -> list[dict]:
        return [p.model_dump() for p in ledger.list_projects()]

    @app.post("/projects")
    def create_project(body: ProjectCreate) -> dict:
        proj = ledger.create_project(body.title, description=body.description, domain=body.domain)
        return proj.model_dump()

    @app.get("/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        proj = ledger.get_project(project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail="project not found")
        return proj.model_dump()

    @app.get("/projects/{project_id}/entities")
    def project_entities(project_id: str) -> list[dict]:
        if ledger.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")
        return ledger.list_entities(project_id)

    @app.get("/projects/{project_id}/provenance")
    def project_provenance(project_id: str) -> list[dict]:
        if ledger.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")
        return ledger.provenance_for_project(project_id)

    # --- Discovery Engine (read-only; execution stays behind the CLI/sandbox) ---
    @app.get("/projects/{project_id}/discovery/{kind}")
    def discovery_objects(project_id: str, kind: str) -> list[dict]:
        from ..discovery.store import DiscoveryStore

        if kind not in {"candidate", "proposal", "tree_node", "tool", "negative"}:
            raise HTTPException(status_code=400, detail="unknown discovery kind")
        store = DiscoveryStore(session_factory, ledger)
        return store.list_objects(project_id, kind=kind)

    @app.get("/projects/{project_id}/discovery/candidates/rejected")
    def rejected_candidates(project_id: str) -> list[dict]:
        from ..discovery.store import DiscoveryStore

        store = DiscoveryStore(session_factory, ledger)
        return store.list_objects(project_id, kind="candidate", status="REJECTED")

    return app


app = create_app()
