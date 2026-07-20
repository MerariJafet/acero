"""Project status narrative — what's done, where we are, what's next, decisions.

Computed from the project's REAL artifacts (hypotheses, experiments, World Model
nodes, dossiers, provenance). Never invents progress: an empty project reports
itself as empty, and recommendations are rule-based on actual state.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger


def build_status(project_id: str, session_factory: Any | None = None) -> dict[str, Any] | None:
    from ..world_model.graph import WorldModel

    sf = session_factory or default_session_factory()
    ledger = ResearchLedger(sf)
    p = ledger.get_project(project_id)
    if p is None:
        return None
    store = DiscoveryStore(sf, ledger)

    hyps = store.list_objects(project_id, kind="candidate")
    approved = [h for h in hyps if (h.get("status") or "").upper() == "APPROVED"]
    exps = store.list_objects(project_id, kind="experiment")
    real_exps = [e for e in exps if e.get("synthetic") is False]
    dossiers = store.list_objects(project_id, kind="dossier")
    literature = store.list_objects(project_id, kind="literature")
    negs = store.list_objects(project_id, kind="negative")
    wm = WorldModel(sf, ledger, project_id)
    nodes = wm.page_nodes(offset=0, limit=10)
    events = ledger.provenance_for_project(project_id)

    # --- pipeline stages (done flags from real artifacts) -------------------
    stages = [
        {"stage": "Proyecto creado", "done": True, "detail": p.created_at[:10]},
        {"stage": "Hipótesis competidoras", "done": bool(hyps),
         "detail": f"{len(hyps)} generadas" if hyps else "ninguna aún"},
        {"stage": "Hipótesis aprobada (humano)", "done": bool(approved),
         "detail": ", ".join(str(h.get("tag") or h.get("id", ""))[:12] for h in approved)
                   or "pendiente"},
        {"stage": "Experimentos ejecutados", "done": bool(exps),
         "detail": f"{len(exps)} en total · {len(real_exps)} con datos reales"},
        {"stage": "Literatura científica indexada", "done": bool(literature),
         "detail": f"{len(literature)} papers reales (con DOI + chequeo de retracción)"
                   if literature else "ninguna aún"},
        {"stage": "Conocimiento registrado (World Model)", "done": nodes["total"] > 0,
         "detail": f"{nodes['total']} nodos"},
        {"stage": "Dossier para revisión humana", "done": bool(dossiers),
         "detail": f"{len(dossiers)} generado(s)" if dossiers else "pendiente"},
        {"stage": "Revisión humana externa", "done": False,
         "detail": "pendiente — siempre es una decisión humana"},
    ]
    current = next((s["stage"] for s in stages if not s["done"]),
                   "Revisión humana externa")

    # --- what was actually done (rich, honest items) ------------------------
    done_items: list[dict[str, Any]] = []
    for h in hyps:
        done_items.append({
            "kind": "hipótesis", "title": f"{h.get('tag', 'H?')}: {h.get('description', '')}",
            "status": h.get("status", ""),
            "note": "sintética (plantilla del ciclo)" if h.get("synthetic") else ""})
    for e in exps:
        if e.get("synthetic") is False:
            fitted = e.get("fitted") or {}
            done_items.append({
                "kind": "experimento REAL", "title": e.get("claim", "verificación con datos reales"),
                "status": "COMPLETO",
                "note": f"dataset: {e.get('dataset','')} · n={e.get('n_planets','?')} · "
                        f"R²={fitted.get('r_squared','?')}"})
        else:
            done_items.append({
                "kind": "experimento sintético", "title": f"{e.get('id','')} (R²={e.get('r2','?')})",
                "status": e.get("status", ""),
                "note": "demostración del flujo, NO una observación"})
    for item in nodes.get("items", []):
        done_items.append({"kind": "conocimiento", "title": item.get("label", ""),
                           "status": f"confianza {item.get('confidence')}",
                           "note": "claim bajo revisión — no es un hecho confirmado"})
    by_angle: dict[str, int] = {}
    for lp in literature:
        by_angle[lp.get("angle", "general")] = by_angle.get(lp.get("angle", "general"), 0) + 1
    for angle, cnt in by_angle.items():
        done_items.append({"kind": "literatura", "title": f"{cnt} papers reales sobre «{angle}»",
                           "status": "INDEXADO", "note": "fuente real (Crossref) con DOI y procedencia"})
    for d in dossiers:
        title = d.get("claim") or ("investigación a fondo" if d.get("kind") == "deep_investigation"
                                   else d.get("id", ""))
        done_items.append({"kind": "dossier", "title": title,
                           "status": d.get("readiness", ""), "note": "requiere revisión humana"})

    # --- decisions taken (from provenance, human/gate actions) --------------
    decisions: list[dict[str, str]] = []
    for e in events:
        s = (e.get("summary") or "")
        low = s.lower()
        if "approved" in low or "aprob" in low:
            decisions.append({"at": str(e.get("at") or e.get("timestamp") or "")[:19],
                              "actor": str(e.get("actor", "")), "decision": s[:140]})
    if not decisions:
        decisions.append({"at": "", "actor": "—",
                          "decision": "Aún no se han tomado decisiones humanas registradas."})

    # --- recommended next steps (rule-based, honest) ------------------------
    next_steps: list[dict[str, str]] = []
    if not hyps:
        next_steps.append({"tab": "research",
                           "text": "Genera hipótesis competidoras (Investigar → Lanzar ciclo)"})
    elif not approved:
        next_steps.append({"tab": "research",
                           "text": "Aprueba una hipótesis con una razón explícita"})
    if not real_exps:
        next_steps.append({"tab": "research",
                           "text": "Ancla el proyecto a evidencia: Verificar con datos reales (NASA)"})
    next_steps.append({"tab": "lit",
                       "text": "Busca literatura real para contexto y CONTRAevidencia"})
    if not dossiers:
        next_steps.append({"tab": "research",
                           "text": "Cuando haya evidencia suficiente, genera el dossier para revisión"})
    next_steps.append({"tab": "learn",
                       "text": "Domina los conceptos BLOQUEANTES antes de aprobar un dossier"})
    next_steps.append({"tab": "chat",
                       "text": "Pide al Copiloto un plan detallado del siguiente experimento"})

    return {
        "project_id": project_id, "title": p.title, "domain": p.domain,
        "stages": stages, "current_stage": current,
        "done_items": done_items, "n_done": len(done_items),
        "decisions": decisions, "next_steps": next_steps,
        "negatives": len(negs), "events": len(events),
        "honesty": ("Nada aquí es un descubrimiento. Los experimentos sintéticos son "
                    "demostraciones de flujo; los claims son creencias bajo revisión; "
                    "el techo es la revisión humana."),
    }
