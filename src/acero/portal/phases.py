"""Investigation phases — map a project's REAL artifacts to the 6-phase research flow.

Fases: Hipótesis → Investigación de literatura → Teorías → Experimentos →
Resultados → Conclusiones. Cada fase reporta conteos, items y un estado honesto
derivado exclusivamente de artefactos reales (nunca progreso inventado).
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

PHASES = ["hipotesis", "literatura", "teorias", "experimentos", "resultados", "conclusiones"]

_TITLES = {
    "hipotesis": "Hipótesis",
    "literatura": "Investigación de literatura",
    "teorias": "Teorías / Conocimiento",
    "experimentos": "Experimentos",
    "resultados": "Resultados",
    "conclusiones": "Conclusiones",
}
_ICONS = {"hipotesis": "🧪", "literatura": "📚", "teorias": "🧠",
          "experimentos": "⚗️", "resultados": "📊", "conclusiones": "📜"}


def build_phases(project_id: str, session_factory: Any | None = None) -> dict[str, Any] | None:
    from ..world_model.graph import WorldModel

    sf = session_factory or default_session_factory()
    ledger = ResearchLedger(sf)
    p = ledger.get_project(project_id)
    if p is None:
        return None
    store = DiscoveryStore(sf, ledger)

    hyps = store.list_objects(project_id, kind="candidate")
    lit = store.list_objects(project_id, kind="literature")
    exps = store.list_objects(project_id, kind="experiment")
    real_exps = [e for e in exps if e.get("synthetic") is False]
    negs = store.list_objects(project_id, kind="negative")
    dossiers = store.list_objects(project_id, kind="dossier")
    wm = WorldModel(sf, ledger, project_id)
    nodes = wm.page_nodes(offset=0, limit=25)

    approved = [h for h in hyps if (h.get("status") or "").upper() == "APPROVED"]

    # results = experiment outcomes (metrics/claims) + preserved negatives
    results_items: list[dict[str, Any]] = []
    for e in exps:
        res = e.get("result") or {}
        claim = e.get("claim") or res.get("claim") or ""
        if claim or res:
            results_items.append({
                "title": (claim or e.get("id", ""))[:140],
                "meta": ("datos reales" if e.get("synthetic") is False else "sintético"),
                "angle": e.get("angle", "")})
    for n in negs:
        results_items.append({"title": str(n.get("summary") or n.get("id", ""))[:140],
                              "meta": "resultado negativo (preservado)", "angle": ""})

    conclusions_items = [{
        "title": (d.get("synthesis") or d.get("claim") or "dossier")[:200],
        "meta": f"{d.get('readiness','')} · {d.get('status','')}",
        "id": d.get("id", "")} for d in dossiers]

    def _status(count: int, active_note: str, empty_note: str) -> dict[str, Any]:
        return {"count": count,
                "state": "done" if count else "pending",
                "note": active_note if count else empty_note}

    phases = {
        "hipotesis": {
            **_status(len(hyps), f"{len(approved)} aprobada(s) de {len(hyps)}",
                      "sin hipótesis aún"),
            "items": [{"title": f"{h.get('tag','H?')}: {h.get('description','')}",
                       "meta": h.get("status", ""),
                       "flag": "sintética" if h.get("synthetic") else ""} for h in hyps],
        },
        "literatura": {
            **_status(len(lit), "papers reales con DOI + chequeo de retracción",
                      "sin literatura indexada"),
            "items": [{"title": (li.get("title") or li.get("doi", ""))[:120],
                       "meta": f"{li.get('doi','')} · {li.get('angle','')}",
                       "url": li.get("url", ""),
                       "flag": "RETRACTADO" if li.get("integrity") == "retracted" else ""}
                      for li in lit],
        },
        "teorias": {
            **_status(int(nodes["total"]), "claims bajo revisión en el World Model",
                      "sin nodos de conocimiento"),
            "items": [{"title": n.get("label", ""),
                       "meta": f"confianza {n.get('confidence')}"} for n in nodes["items"]],
        },
        "experimentos": {
            **_status(len(exps), f"{len(real_exps)} con datos reales", "sin experimentos"),
            "items": [{"title": (e.get("claim") or e.get("id", ""))[:120],
                       "meta": ("DATOS REALES · " + str(e.get("angle") or e.get("dataset") or ""))
                               if e.get("synthetic") is False else "sintético (flujo)"}
                      for e in exps],
        },
        "resultados": {
            **_status(len(results_items), f"{len(negs)} negativos preservados",
                      "sin resultados aún"),
            "items": results_items,
        },
        "conclusiones": {
            **_status(len(dossiers), "esperan revisión humana", "sin conclusiones aún"),
            "items": conclusions_items,
        },
    }
    for key, ph in phases.items():
        ph["key"] = key
        ph["title"] = _TITLES[key]
        ph["icon"] = _ICONS[key]

    n_done = sum(1 for ph in phases.values() if ph["state"] == "done")
    return {
        "project_id": project_id, "title": p.title, "domain": p.domain,
        "state": p.state.value, "created_at": p.created_at,
        "phases": [phases[k] for k in PHASES],
        "n_phases_done": n_done, "n_phases": len(PHASES),
        "progress_pct": round(100 * n_done / len(PHASES)),
        "honesty": ("Fases derivadas de artefactos reales; nada es un descubrimiento; "
                    "el techo es la revisión humana."),
    }
