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

    # --- World Model (read-only) ---
    def _wm(project_id: str):
        from ..world_model.graph import WorldModel

        return WorldModel(session_factory, ledger, project_id)

    @app.get("/projects/{project_id}/world/stats")
    def world_stats(project_id: str) -> dict:
        return _wm(project_id).stats()

    @app.get("/projects/{project_id}/world/nodes")
    def world_nodes(project_id: str) -> list[dict]:
        return [n.model_dump() for n in _wm(project_id).nodes()]

    @app.get("/projects/{project_id}/world/narrate")
    def world_narrate(project_id: str) -> list[dict]:
        from ..world_model.narrate import narrate

        return narrate(_wm(project_id))

    @app.get("/projects/{project_id}/world/query/{what}")
    def world_query(project_id: str, what: str) -> dict:
        from collections.abc import Callable

        from ..world_model.queries import ScientificMemory

        mem = ScientificMemory(_wm(project_id))
        options: dict[str, Callable[[], object]] = {
            "anomalies": lambda: [a.label for a in mem.open_anomalies()],
            "contradictions": lambda: [c.label for c in mem.open_contradictions()],
            "untested": lambda: [n.label for n in mem.untested_beliefs()],
            "weak": mem.weak_relations,
            "single": lambda: [n.label for n in mem.single_source_claims()],
            "critical": mem.critical_assumptions,
        }
        if what not in options:
            raise HTTPException(status_code=400, detail=f"unknown query '{what}'")
        return {"query": what, "result": options[what]()}

    # --- Cognitive Discovery Engine (read-only + pure math) ---
    @app.get("/cognitive/validate-equation")
    def validate_equation(lhs: str, rhs: str) -> dict:
        from ..cognitive.first_principles.engine import FirstPrinciplesEngine

        try:
            return FirstPrinciplesEngine().validate_equation(lhs, rhs)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/cognitive/analogy/{pair}")
    def analogy_benchmark(pair: str) -> dict:
        from ..cognitive.analogies.engine import AnalogyEngine
        from ..cognitive.analogies.systems import BENCHMARK_PAIRS
        from ..world_model.graph import WorldModel

        if pair not in BENCHMARK_PAIRS:
            raise HTTPException(status_code=404, detail="unknown pair")
        wm = WorldModel(session_factory, ledger, "ephemeral")
        a = AnalogyEngine(wm).build(*BENCHMARK_PAIRS[pair], run_transfer=False)
        return {"status": a.status.value, "deep_score": a.scores.deep_score(),
                "surface_similarity": a.scores.surface_similarity,
                "mapping": a.entity_mapping,
                "validations": {v.test: v.passed for v in a.validations}}

    @app.get("/projects/{project_id}/cognitive/analogies")
    def project_analogies(project_id: str) -> list[dict]:
        from ..cognitive.analogies.engine import AnalogyEngine
        from ..world_model.graph import WorldModel

        wm = WorldModel(session_factory, ledger, project_id)
        return [a.model_dump() for a in AnalogyEngine(wm).analogies()]

    # --- Governing Structure Inference (read-only + pure computation) ---
    @app.get("/inference/discover/{system}")
    def inference_discover(system: str) -> dict:
        from ..inference.data.observations import generate
        from ..inference.engine import StructureInferenceEngine
        from ..inference.models import StructureInferenceProblem

        systems = ["exponential_decay", "logistic", "harmonic", "damped", "predator_prey"]
        if system not in systems:
            raise HTTPException(status_code=404, detail=f"unknown system; {systems}")
        obs = generate(system, seed=1, n=400, t_max=8.0)
        prob = StructureInferenceProblem(project_id="api", phenomenon=system,
                                         variables_observed=obs.variables)
        rep = StructureInferenceEngine().infer(prob, obs, threshold=0.2)
        return {"system": system, "inference_level": rep["inference_level"],
                "equations": {k: v["expression"] for k, v in rep["equations"].items()},
                "invariants": rep["invariants"], "abstention": rep["abstention"],
                "imposed": rep["imposed"]}

    @app.get("/inference/benchmark")
    def inference_benchmark_endpoint() -> dict:
        from ..benchmarks.governing_dynamics import run_governing_dynamics

        r = run_governing_dynamics()
        return {"level1": {k: v["recovered"] for k, v in r["level1_recovery"].items()},
                "level5_regime": r["level5_regime"]["regime_change_detected"],
                "level7_gate": r["level7_adversarial_gate"]["status"]}

    return app


app = create_app()
