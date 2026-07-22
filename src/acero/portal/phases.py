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

# Explicación honesta por fase: qué es, de dónde sale, y qué significa su "calificación".
_METHODOLOGY = {
    "hipotesis": {
        "que_es": "Marcos competidores que explican el fenómeno, INCLUIDA la nula (H0).",
        "de_donde": "Generadas como plantilla del ciclo de investigación o propuestas por "
                    "el copiloto (Codex CLI local). No son afirmaciones, son candidatos a probar.",
        "calificacion": "El estado APPROVED significa que un humano la marcó con una razón "
                        "explícita; PROPOSED = aún sin aprobar. Aprobar ≠ que sea verdadera.",
    },
    "literatura": {
        "que_es": "Publicaciones científicas reales relacionadas con la pregunta.",
        "de_donde": "Recuperadas EN VIVO de Crossref (agregador oficial de metadatos) por el "
                    "Knowledge Mesh. Cada una trae DOI, autores y licencia reales.",
        "calificacion": "Cada paper se verifica contra RETRACCIÓN con una consulta inversa a "
                        "Crossref (¿algún trabajo lo retracta?). «RETRACTADO» = sí; se conserva "
                        "y se marca, nunca se borra.",
    },
    "teorias": {
        "que_es": "Nodos del World Model: creencias/claims bajo revisión (no hechos).",
        "de_donde": "Se crean al registrar un resultado o una relación durante la investigación, "
                    "con procedencia (quién y cuándo).",
        "calificacion": "La CONFIANZA (0–1) es un valor de creencia INICIAL asignado al crear el "
                        "nodo — NO es una probabilidad de verdad ni evidencia. Solo sube con "
                        "evidencia independiente y replicación; aquí no se ha calibrado, por eso "
                        "es baja. Un claim con confianza alta seguiría necesitando revisión humana.",
    },
    "experimentos": {
        "que_es": "Análisis ejecutados sobre datos.",
        "de_donde": "Los REALES usan datos públicos verificables (p.ej. catálogo NASA de "
                    "exoplanetas, mediciones de H0); los SINTÉTICOS son demostración del flujo "
                    "y no son observaciones.",
        "calificacion": "Métricas como R² (bondad de ajuste) o σ (nivel de tensión) se calculan "
                        "sobre los datos reales; un R² alto indica consistencia con un modelo "
                        "conocido, NO un descubrimiento.",
    },
    "resultados": {
        "que_es": "Salidas de los experimentos (claims con métricas) y resultados negativos.",
        "de_donde": "Derivados directamente de los experimentos; los negativos se PRESERVAN "
                    "(nunca se ocultan) porque son parte del método honesto.",
        "calificacion": "«datos reales» vs «sintético» indica el origen; un negativo preservado "
                        "es tan valioso como uno positivo.",
    },
    "conclusiones": {
        "que_es": "Dossiers: síntesis para revisión humana.",
        "de_donde": "Compilan hipótesis, literatura, experimentos y sus límites. La síntesis IA "
                    "(Codex) es ayuda de razonamiento, NO evidencia.",
        "calificacion": "Readiness EXPLORATORY = preliminar; el techo SIEMPRE es la revisión "
                        "humana externa. Nunca se publica automáticamente.",
    },
}


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

    # newest critique of "El Revisor" per target entity (footer on each card)
    crits: dict[str, dict[str, Any]] = {}
    for c in store.list_objects(project_id, kind="critique"):
        t = c.get("target_id", "")
        if t and (t not in crits
                  or (c.get("created_at") or "") > (crits[t].get("created_at") or "")):
            crits[t] = c

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
            "items": [{"id": h.get("id", ""), "tag": h.get("tag", "H?"),
                       "title": h.get("title") or h.get("description", ""),
                       "meta": h.get("status", ""),
                       "kind": h.get("kind", ""),
                       "trigger_question": h.get("trigger_question", ""),
                       "argument": h.get("argument", ""), "doubt": h.get("doubt", ""),
                       "test_idea": h.get("test_idea", ""),
                       "competes_with": h.get("competes_with", ""),
                       "provider": h.get("provider", ""),
                       "critique": crits.get(h.get("id", "")),
                       "version": int(h.get("version", 1)),
                       "origin": h.get("origin", ""),
                       "anomaly_provenance": h.get("anomaly_provenance"),
                       "flag": "plantilla" if h.get("synthetic") else ""} for h in hyps],
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
    # --- horizontal bar data per phase (real distributions, CIO-style) ------
    def _bars(pairs: list[tuple[str, float, str]]) -> list[dict[str, Any]]:
        mx = max((v for _, v, _ in pairs), default=0) or 1
        return [{"label": lb, "value": v, "pct": round(100 * v / mx),
                 "right": rt or str(int(v))} for lb, v, rt in pairs if v > 0]

    by_angle: dict[str, int] = {}
    for li in lit:
        a = li.get("angle") or "general"
        by_angle[a] = by_angle.get(a, 0) + 1
    phases["hipotesis"]["bars"] = _bars([
        ("Aprobadas", len(approved), f"{len(approved)}"),
        ("Propuestas", len(hyps) - len(approved), f"{len(hyps) - len(approved)}")])
    phases["literatura"]["bars"] = _bars([
        (a.replace("_", " "), n, f"{n} papers")
        for a, n in sorted(by_angle.items(), key=lambda x: -x[1])[:6]])
    phases["teorias"]["bars"] = [
        {"label": (n.get("label") or "")[:52], "value": n.get("confidence") or 0,
         "pct": round(100 * float(n.get("confidence") or 0)),
         "right": f"confianza {n.get('confidence')}"}
        for n in nodes["items"][:6]]
    phases["experimentos"]["bars"] = _bars([
        ("Con datos reales", len(real_exps), f"{len(real_exps)}"),
        ("Sintéticos (flujo)", len(exps) - len(real_exps), f"{len(exps) - len(real_exps)}")])
    phases["resultados"]["bars"] = _bars([
        ("Resultados con claim", len(results_items) - len(negs), ""),
        ("Negativos preservados", len(negs), "")])
    by_ready: dict[str, int] = {}
    for d in dossiers:
        by_ready[d.get("readiness") or "?"] = by_ready.get(d.get("readiness") or "?", 0) + 1
    phases["conclusiones"]["bars"] = _bars([(k, v, f"{v}") for k, v in by_ready.items()])

    # dedup the theory items for display (repeated runs can create identical claims)
    seen_labels: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for it in phases["teorias"]["items"]:
        if it["title"] not in seen_labels:
            seen_labels.add(it["title"])
            deduped.append(it)
    if len(deduped) < len(phases["teorias"]["items"]):
        phases["teorias"]["note"] += f" · {len(deduped)} únicos de {int(nodes['total'])}"
    phases["teorias"]["items"] = deduped

    for key, ph in phases.items():
        ph["key"] = key
        ph["title"] = _TITLES[key]
        ph["icon"] = _ICONS[key]
        ph["methodology"] = _METHODOLOGY.get(key, {})

    # KPIs for the top strip
    kpis = {
        "papers": len(lit), "experiments": len(exps), "real_experiments": len(real_exps),
        "hypotheses": len(hyps), "approved": len(approved),
        "nodes": int(nodes["total"]), "dossiers": len(dossiers), "negatives": len(negs),
        "real_pct": round(100 * len(real_exps) / len(exps)) if exps else 0,
        "approved_pct": round(100 * len(approved) / len(hyps)) if hyps else 0,
    }

    n_done = sum(1 for ph in phases.values() if ph["state"] == "done")
    # one-line narrative (CIO-style summary sentence), from real state
    if n_done == 0:
        narrative = "Investigación creada, sin trabajo aún — empieza generando hipótesis."
    else:
        parts = []
        if real_exps:
            parts.append(f"{len(real_exps)} experimento(s) con datos reales")
        if lit:
            parts.append(f"{len(lit)} papers reales indexados")
        if dossiers:
            parts.append(f"{len(dossiers)} dossier(s) esperando tu revisión")
        narrative = ("La investigación avanza: " + ", ".join(parts) +
                     ". Nada es un descubrimiento; el techo es la revisión humana.")
    return {
        "project_id": project_id, "title": p.title, "domain": p.domain,
        "state": p.state.value, "created_at": p.created_at,
        "phases": [phases[k] for k in PHASES],
        "n_phases_done": n_done, "n_phases": len(PHASES),
        "progress_pct": round(100 * n_done / len(PHASES)),
        "kpis": kpis, "narrative": narrative,
        "honesty": ("Fases derivadas de artefactos reales; nada es un descubrimiento; "
                    "el techo es la revisión humana."),
    }
