"""Per-project Research Copilot — a Codex-backed scientific assistant + agentic runner.

Two capabilities per project:
  1) chat(): a specialized scientific-research assistant grounded in the project's
     REAL state and ACERO's methodology. The LLM is a drafting/reasoning aid — its
     output is NEVER treated as scientific evidence and it may never claim a
     discovery. It proposes questions, competing hypotheses, experiments, data, null
     tests and when to abstain.
  2) run_research_cycle(): executes ACERO's REAL research flow on the project
     (hypotheses -> approve -> experiment -> gate -> World Model -> dossier) through
     the same gate-guarded services the CLI uses, writing real artifacts + provenance
     so the project shows genuine progress. Synthetic steps are labelled synthetic.
"""

from __future__ import annotations

import time
from typing import Any

from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

SYSTEM = """\
Eres el Copiloto Científico de ACERO para un proyecto de investigación. ACERO es un
sistema de descubrimiento local-first con humano-en-el-circuito. Tu trabajo es reducir
la incertidumbre con rigor, NO impresionar.

REGLAS NO NEGOCIABLES:
- Nunca afirmes un descubrimiento. El techo epistemológico es la revisión humana.
- Tu salida es una AYUDA de razonamiento/redacción; NUNCA es evidencia científica.
- Recuperar una señal conocida no es descubrir; una señal inyectada no es una observación;
  dos pipelines sobre los mismos datos no son replicación independiente.
- Propón: preguntas acotadas, hipótesis COMPETIDORAS (incluida la nula), datos públicos
  con licencia, experimentos, pruebas nulas, escenarios de falso positivo, y CUÁNDO
  ABSTENERSE. Sé honesto sobre límites y lo que NO se puede concluir.
- Responde claro, en el idioma del usuario, con pasos accionables para este proyecto.
"""


class ResearchCopilot:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- grounding -------------------------------------------------------
    def project_context(self, project_id: str) -> dict[str, Any]:
        from ..world_model.graph import WorldModel
        p = self.ledger.get_project(project_id)
        if p is None:
            return {}
        hyps = self.store.list_objects(project_id, kind="candidate")
        exps = self.store.list_objects(project_id, kind="experiment")
        negs = self.store.list_objects(project_id, kind="negative")
        wm = WorldModel(self._sf, self.ledger, project_id).stats()
        ev = self.ledger.provenance_for_project(project_id)
        return {
            "id": p.id, "title": p.title, "domain": p.domain, "state": p.state.value,
            "hypotheses": len(hyps), "experiments": len(exps), "negatives": len(negs),
            "world_nodes": int(wm.get("n_nodes", 0)), "events": len(ev),
            "hypothesis_tags": [h.get("tag") for h in hyps][:8],
        }

    def _prompt(self, ctx: dict[str, Any], message: str) -> str:
        state = (f"Proyecto: {ctx.get('title')} (dominio {ctx.get('domain')}).\n"
                 f"Estado real: {ctx.get('hypotheses',0)} hipótesis, "
                 f"{ctx.get('experiments',0)} experimentos, "
                 f"{ctx.get('world_nodes',0)} nodos de World Model, "
                 f"{ctx.get('events',0)} eventos. "
                 f"{'VACÍO — aún sin trabajo.' if ctx.get('events',0)<=1 else ''}")
        return f"{SYSTEM}\n\n[CONTEXTO DEL PROYECTO]\n{state}\n\n[USUARIO]\n{message}\n\n[COPILOTO]"

    def chat(self, project_id: str, message: str, *, timeout_sec: int = 180) -> dict[str, Any]:
        ctx = self.project_context(project_id)
        if not ctx:
            return {"ok": False, "error": "project not found"}
        prompt = self._prompt(ctx, message)
        from ..llm.providers import CodexCliProvider
        prov = CodexCliProvider(timeout_sec=timeout_sec)
        if not prov.available():
            return {"ok": True, "provider": "unavailable", "context": ctx,
                    "reply": ("El motor Codex no está disponible en este entorno. "
                              "Puedo seguir guiando el método, pero sin generación IA.")}
        t0 = time.time()
        try:
            resp = prov.complete(prompt, temperature=0.2, max_tokens=1200)
            reply = resp.text
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"copilot error: {exc}", "context": ctx}
        return {"ok": True, "provider": "codex", "context": ctx, "reply": reply,
                "usage": getattr(prov, "last_usage", {}),
                "elapsed_sec": round(time.time() - t0, 1),
                "disclaimer": "Salida de IA: ayuda de razonamiento, NO evidencia científica."}


def run_real_data_verification(project_id: str, *, session_factory: Any | None = None
                               ) -> dict[str, Any]:
    """Run a REAL data-backed verification (Kepler's 3rd law on NASA data) and record it."""
    from ..core.ids import new_id
    from ..studies.kepler_law import verify
    from ..world_model.graph import WorldModel
    from ..world_model.nodes import NodeType

    sf = session_factory or default_session_factory()
    ledger = ResearchLedger(sf)
    if ledger.get_project(project_id) is None:
        return {"ok": False, "error": "project not found"}
    res = verify()
    if not res.get("ok"):
        return {"ok": False, "error": res.get("reason", "verification failed")}

    store = DiscoveryStore(sf, ledger)
    eid = new_id("exp")
    store.put(project_id, "experiment", eid, {
        "id": eid, "kind": "real_data_verification", "synthetic": False,
        "dataset": res["source"], "n_planets": res["n_planets"],
        "fitted": res["fitted"], "earth_context": res["earth_context"],
        "consistent_with_kepler": res["consistent_with_kepler"], "claim": res["claim"]},
        status="COMPLETE", actor="copilot",
        summary=f"real-data Kepler verification (n={res['n_planets']}, R2={res['fitted']['r_squared']})")
    wm = WorldModel(sf, ledger, project_id)
    node = wm.create(NodeType.CLAIM,
                     f"Órbita de la Tierra consistente con Kepler (R²={res['fitted']['r_squared']})",
                     confidence=0.6)
    return {"ok": True, "experiment_id": eid, "world_node": node.id, "result": res,
            "is_discovery": False}


def run_research_cycle(project_id: str, question: str, *, session_factory: Any | None = None
                       ) -> dict[str, Any]:
    """Execute one REAL ACERO research cycle on an existing project (gate-guarded)."""
    from .workspace import WorkspaceService
    ws = WorkspaceService(session_factory)
    if ws.ledger.get_project(project_id) is None:
        return {"ok": False, "error": "project not found"}

    steps: list[dict[str, Any]] = []
    hyps = ws.generate_hypotheses(project_id, question)
    steps.append({"step": "hypotheses", "created": len(hyps),
                  "tags": [h["tag"] for h in hyps]})
    appr = ws.approve_hypothesis(hyps[0]["id"], f"copiloto: hipótesis competidora para «{question}»")
    steps.append({"step": "approve", "approved": appr["tag"]})
    exp = ws.run_experiment(project_id, hyps[0]["id"])
    steps.append({"step": "experiment", "id": exp["id"], "r2": exp["r2"], "synthetic": True})
    gate_ok = ws.gate_check(exp)
    gate_bad = ws.gate_check({"dimensions_valid": False, "train_test_disjoint": False,
                              "reproduced": False, "codex_treated_as_evidence": True})
    steps.append({"step": "gate", "valid_artifact": gate_ok["outcome"],
                  "invalid_artifact": gate_bad["outcome"]})
    node = ws.update_world_model(project_id, f"claim (bajo revisión): {question[:60]}")
    steps.append({"step": "world_model", "node_id": node["node_id"]})
    doss = ws.dossier(project_id, f"verificación computacional preliminar: {question[:60]}")
    steps.append({"step": "dossier", "id": doss["id"], "readiness": doss["readiness"],
                  "auto_publish": doss["can_publish_automatically"]})
    return {"ok": True, "question": question, "steps": steps, "is_discovery": False,
            "note": ("Ciclo REAL ejecutado por servicios gate-guardados. El experimento es "
                     "SINTÉTICO (demostración del flujo), no una observación. Sin descubrimiento.")}
