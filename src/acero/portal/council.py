"""El Consejo — the 14 scientist-personas of ACERO as a dashboard view.

Each persona IS a real flow of the program (module in parentheses). This module is the
single source of truth: names, roles, stage, module, maturity status, hand-offs, summary,
face parameters and the task list travel to the frontend as JSON, so `council.js` is a
pure renderer.

Per-project PROGRESS is computed from the project's REAL KPIs (from `build_phases`) where a
persona maps to a measurable signal (Hilbert↔hypotheses, Da Vinci↔experiments, Kepler↔
approved, Gauss↔dossiers…); personas without a direct project signal fall back to their
capability MATURITY (green/amber/blue/red). This mix is intentional and honest — see the
`source` field on each persona ('project' vs 'maturity').
"""

from __future__ import annotations

from typing import Any

# maturity → baseline progress when there is no direct project signal
_BASE = {"good": 88, "warn": 60, "new": 55, "weak": 32}

STAGES = [
    {"key": "plantear", "name": "Plantear", "ids": ["hilbert", "euler", "hipatia"]},
    {"key": "explorar", "name": "Explorar / crear",
     "ids": ["arquimedes", "davinci", "kepler", "tycho"]},
    {"key": "confrontar", "name": "Confrontar",
     "ids": ["popper", "euclides", "godel", "aristoteles"]},
    {"key": "segunda", "name": "Segunda jugada", "ids": ["feynman", "bohr"]},
    {"key": "publicar", "name": "Publicar", "ids": ["gauss"]},
]

# the 3 macro-phases (the pies) and which persona lives in each
PHASES = [
    {"key": "creativa", "name": "Fase Creativa", "sub": "idear · plantear · explorar",
     "ids": ["hilbert", "arquimedes", "davinci", "kepler", "feynman"]},
    {"key": "investig", "name": "Fase de Investigación", "sub": "buscar · registrar · dirigir",
     "ids": ["euler", "hipatia", "tycho", "bohr"]},
    {"key": "critica", "name": "Fase Crítica", "sub": "probar · refutar · publicar",
     "ids": ["popper", "euclides", "godel", "aristoteles", "gauss"]},
]
_PHASE_OF = {pid: ph["key"] for ph in PHASES for pid in ph["ids"]}

# face params drive the vector portrait in council.js
PERSONAS: list[dict[str, Any]] = [
    {"id": "hilbert", "name": "Hilbert", "role": "Plantea conjeturas precisas",
     "module": "question_engine", "status": "warn", "hands_to": "Hipatia", "awaits": "—",
     "summary": "Formula problemas falsables y fértiles — el punto de partida de toda investigación.",
     "face": {"hair": "recede", "beard": "full", "hairc": "#d9d2c4"},
     "tasks": [["Generar conjeturas", "done"], ["Evitar bordes triviales", "doing"],
               ["Priorizar por fertilidad", "todo"]]},
    {"id": "euler", "name": "Euler", "role": "Genera hipótesis en masa y filtra",
     "module": "sweep.py", "status": "warn", "hands_to": "Bohr", "awaits": "Hilbert",
     "summary": "Barrido masivo en paralelo: produce muchas hipótesis y las filtra por novedad y vulnerabilidad.",
     "face": {"hair": "short", "hairc": "#e6dccb", "skin": 2},
     "tasks": [["Barrido paralelo", "done"], ["Filtro EVA+novedad", "done"],
               ["Rodaje reciente", "todo"]]},
    {"id": "hipatia", "name": "Hipatia", "role": "¿Ya se hizo? Novedad multi-fuente",
     "module": "novelty_check.py", "status": "good", "hands_to": "Bohr", "awaits": "Hilbert",
     "summary": "Redacta consultas de experto y busca en OpenAlex+arXiv+Crossref; distingue descubrimiento de recuperación.",
     "face": {"hair": "bun", "hairc": "#3a2f26", "skin": 3, "accent": "#54c08a"},
     "tasks": [["Query-craft (LLM)", "done"], ["Multi-fuente + dedup", "done"],
               ["Juez + timeout paciente", "done"]]},
    {"id": "arquimedes", "name": "Arquímedes", "role": "La caja de piezas LEGO",
     "module": "method_catalog.py", "status": "new", "hands_to": "Da Vinci", "awaits": "—",
     "summary": "Catálogo curado de técnicas (grafos, teoría de números, Z3, optimización…) que el programa posee.",
     "face": {"hair": "wild", "beard": "full", "hairc": "#e6dccb"},
     "tasks": [["26 piezas curadas", "done"], ["Retrieval determinista", "done"],
               ["Crecer con learn()", "doing"]]},
    {"id": "davinci", "name": "Da Vinci", "role": "Explora múltiples enfoques",
     "module": "math_explorer.py", "status": "good", "hands_to": "Kepler",
     "awaits": "Arquímedes",
     "summary": "De un objetivo, diverge en enfoques creativos y corre cada uno como script en el sandbox.",
     "face": {"hair": "long", "beard": "full", "hairc": "#d8cbb4", "accent": "#54c08a"},
     "tasks": [["Diverge K enfoques", "done"], ["Corre en paralelo", "done"],
               ["10/10 correctas", "done"]]},
    {"id": "kepler", "name": "Kepler", "role": "Sintetiza la hipótesis",
     "module": "_synthesize", "status": "warn", "hands_to": "Popper", "awaits": "Da Vinci",
     "summary": "Destila una ley precisa de los enfoques que funcionaron y le da forma formal.",
     "face": {"hair": "short", "beard": "mous", "hairc": "#cbb89c", "hat": "ruff"},
     "tasks": [["Destilar hipótesis", "done"], ["Forma formal fiable", "doing"],
               ["Codificar sumatorias", "todo"]]},
    {"id": "tycho", "name": "Tycho", "role": "Registra qué funcionó",
     "module": "explorer_ledger.py", "status": "new", "hands_to": "—", "awaits": "Kepler",
     "summary": "Memoria persistente de los caminos que sirvieron; los reofrece como pistas en el futuro.",
     "face": {"hair": "short", "beard": "full", "nose": "metal", "hairc": "#d9cdb8"},
     "tasks": [["Persistir resultados", "done"], ["Reofrecer pistas", "done"],
               ["Explotar más memoria", "todo"]]},
    {"id": "popper", "name": "Popper", "role": "Refuta: busca contraejemplos",
     "module": "math_probe.py", "status": "good", "hands_to": "Bohr", "awaits": "Kepler",
     "summary": "Ataca cada hipótesis buscando contraejemplos; ya no refuta en falso (regla anti-near-miss).",
     "face": {"hair": "recede", "glasses": 1, "hairc": "#d9d2c4", "accent": "#54c08a"},
     "tasks": [["Codegen contraejemplos", "done"], ["Regla anti-refutación-falsa", "done"],
               ["Sin falsos en Basilea/√π", "done"]]},
    {"id": "euclides", "name": "Euclides", "role": "Prueba formal (sympy)",
     "module": "formal_verify.py", "status": "good", "hands_to": "Bohr", "awaits": "Popper",
     "summary": "Demuestra álgebra y análisis: identidades, desigualdades, sumatorias, límites.",
     "face": {"hair": "short", "beard": "full", "hairc": "#e6dccb", "hat": "laurel",
              "accent": "#54c08a"},
     "tasks": [["Identidades/límites", "done"], ["Sumatorias/productos", "done"]]},
    {"id": "godel", "name": "Gödel", "role": "Prueba lógica/conteo (Z3)",
     "module": "proof_assistant.py", "status": "good", "hands_to": "Bohr", "awaits": "Feynman",
     "summary": "Motor SMT: demuestra lógica, conteo y cuantificadores donde sympy no llega. Cerró la conjetura B.",
     "face": {"hair": "short", "glasses": 1, "hairc": "#cfc6b4", "accent": "#54c08a"},
     "tasks": [["Backend Z3", "done"], ["Enchufado al loop", "done"],
               ["Backend Lean", "todo"]]},
    {"id": "aristoteles", "name": "Aristóteles", "role": "Corrobora, frena falsedades",
     "module": "guardas + EVA", "status": "good", "hands_to": "Popper", "awaits": "Popper",
     "summary": "El crítico: exige corroboración; degrada refutaciones no confirmadas a revisión humana.",
     "face": {"hair": "short", "beard": "full", "hairc": "#dcd3c2", "hat": "laurel",
              "accent": "#54c08a"},
     "tasks": [["Near-miss/cola", "done"], ["Conflicto formal-empírico", "done"],
               ["Consenso de enfoques", "done"]]},
    {"id": "feynman", "name": "Feynman", "role": "Actitud hacker: segunda jugada",
     "module": "HumanAttitude", "status": "new", "hands_to": "Popper / Gödel",
     "awaits": "Bohr",
     "summary": "La chispa creativa: ve lo que otros no ven, refina bordes triviales y reduce a un lema probable.",
     "face": {"hair": "wild", "hairc": "#cbb89c"},
     "tasks": [["Refinar refutaciones", "done"], ["Reducir a lema", "done"],
               ["Más rodaje", "doing"]]},
    {"id": "bohr", "name": "Bohr", "role": "Dirige el bucle",
     "module": "ResearchLoop", "status": "new", "hands_to": "Feynman / Gauss",
     "awaits": "todos",
     "summary": "El director: orquesta probar→actitud→refinar/probar/escalar y decide la disposición final.",
     "face": {"hair": "short", "hairc": "#d9d2c4", "skin": 2},
     "tasks": [["Orquestar el bucle", "done"], ["Disposiciones honestas", "done"],
               ["Ampliar decisiones", "doing"]]},
    {"id": "gauss", "name": "Gauss", "role": "Publica solo lo maduro",
     "module": "external_validation.py", "status": "warn", "hands_to": "revisión humana",
     "awaits": "Bohr",
     "summary": "Pauca sed matura: empaqueta, exige validación externa humana y marca listo para revisión.",
     "face": {"hair": "short", "hairc": "#e6dccb", "skin": 3},
     "tasks": [["Paquete verificable", "done"], ["Motor de attestation", "done"],
               ["Cerrar una publicación", "todo"]]},
]

# distinct engraved-portrait parameters per persona (drive the SVG face in council.js)
_FACES = {
    "hilbert": {"bald": 1, "fringe": 1, "beard": "full", "hairc": "#e8e2d2", "skin": 2,
                "glasses": "pince", "mous": 1},
    "arquimedes": {"hair": "wild", "beard": "long", "hairc": "#efe8d8", "skin": 4,
                   "browc": "#cabfa8"},
    "davinci": {"hair": "long", "beard": "long", "hairc": "#d9cbb0", "skin": 1,
                "accent": "#54c08a", "browc": "#b7a888"},
    "kepler": {"hair": "curly", "beard": "goatee", "mous": 1, "hairc": "#6b4a2f",
               "skin": 1, "hat": "ruff"},
    "feynman": {"hair": "wavy", "hairc": "#3b2f26", "skin": 1, "smile": 1, "browc": "#2c231b"},
    "euler": {"hair": "recede", "hat": "cap", "hatc": "#2f3a54", "hairc": "#d8cfbd",
              "skin": 3, "wide": 1},
    "hipatia": {"hair": "bun", "earring": 1, "hairc": "#2a221c", "skin": 3,
                "accent": "#54c08a", "browc": "#2a221c"},
    "tycho": {"hair": "short", "beard": "full", "mous": 1, "nose": "metal",
              "hairc": "#8a5a34", "skin": 2, "browc": "#6b4527"},
    "bohr": {"hair": "short", "hairc": "#cfc7b6", "skin": 2, "long": 1, "browc": "#8a7f6a"},
    "popper": {"bald": 1, "fringe": 1, "glasses": "square", "hairc": "#b9b2a2", "skin": 2,
               "accent": "#54c08a", "browc": "#7a7060"},
    "euclides": {"hair": "short", "beard": "full", "hat": "laurel", "hairc": "#e6ddca",
                 "skin": 3, "accent": "#54c08a", "browc": "#cfc4ac"},
    "godel": {"hair": "short", "glasses": "round", "hairc": "#2c2620", "skin": 3,
              "long": 1, "accent": "#54c08a", "browc": "#2c2620"},
    "aristoteles": {"bald": 1, "fringe": 1, "beard": "long", "hat": "laurel",
                    "hairc": "#d6cdb8", "skin": 2, "accent": "#54c08a", "browc": "#bcb199"},
    "gauss": {"hair": "recede", "hat": "cap", "hatc": "#241c14", "hairc": "#c9c0ad",
              "skin": 3, "browc": "#8a7f6a"},
}
for _p in PERSONAS:
    _p["face"] = _FACES.get(_p["id"], _p.get("face", {}))


def _clamp(x: float) -> int:
    return max(0, min(100, int(round(x))))


# qué "kind" del ledger es dueño cada personaje → sus fichas reales
OWNER_KIND = {"hilbert": "candidate", "hipatia": "literature", "popper": "experiment",
              "gauss": "dossier", "aristoteles": "critique",
              "feynman": "reformulation", "godel": "lemma"}
KIND_LABEL = {"candidate": "hipótesis", "literature": "literatura",
              "experiment": "experimentos", "dossier": "dossiers", "critique": "objeciones",
              "reformulation": "reformulaciones", "lemma": "lemas y cotas"}


def _card(kind: str, obj: dict[str, Any]) -> dict[str, Any]:
    """Turn a ledger object into a compact card for a persona's panel."""
    o = obj or {}
    if kind == "experiment":
        res = o.get("result") or {}
        return {"title": (o.get("claim") or "experimento")[:140],
                "verdict": res.get("verdict") or "", "by": o.get("method") or ""}
    if kind == "reformulation":
        return {"title": (o.get("statement") or o.get("claim") or "reformulación")[:140],
                "verdict": o.get("angle") or "segunda jugada", "by": ""}
    if kind == "lemma":
        return {"title": (o.get("statement") or o.get("claim") or "lema")[:140],
                "verdict": ("probado" if o.get("proved") else (o.get("status") or "propuesto")),
                "by": o.get("backend") or ""}
    if kind == "candidate":
        return {"title": (o.get("claim") or o.get("statement") or "hipótesis")[:140],
                "verdict": o.get("status") or "", "by": o.get("by") or ""}
    if kind == "dossier":
        return {"title": (o.get("synthesis") or o.get("claim") or "dossier")[:140],
                "verdict": o.get("readiness") or "", "by": ""}
    if kind == "literature":
        return {"title": (o.get("title") or o.get("claim") or "referencia")[:140],
                "verdict": str(o.get("year") or ""), "by": ""}
    return {"title": (o.get("summary") or o.get("claim") or o.get("title") or "—")[:140],
            "verdict": o.get("status") or "", "by": ""}


def council_for(kpis: dict[str, Any] | None,
                verdicts: list[dict[str, Any]] | None = None,
                items: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Assemble the council for one project from its real KPIs."""
    k = kpis or {}
    hyp = int(k.get("hypotheses") or 0)
    appr = int(k.get("approved") or 0)
    exp = int(k.get("experiments") or 0)
    real = int(k.get("real_experiments") or 0)
    doss = int(k.get("dossiers") or 0)
    papers = int(k.get("papers") or 0)

    # personas with a direct project signal → real progress; others → maturity baseline
    project_signal = {
        "hilbert": min(100, hyp * 12),
        "euler": min(100, hyp * 9),
        "davinci": min(100, exp * 13),
        "kepler": min(100, appr * 16),
        "popper": min(100, exp * 11 + real * 4),
        "tycho": min(100, (exp + appr) * 8),
        "gauss": min(100, (doss + papers) * 24),
    }

    out = []
    prog_by = {}
    for p in PERSONAS:
        if p["id"] in project_signal and (hyp or exp or appr or doss):
            prog, source = _clamp(project_signal[p["id"]]), "project"
        else:
            prog, source = _BASE.get(p["status"], 50), "maturity"
        prog_by[p["id"]] = prog
        entry = {**p, "phase": _PHASE_OF.get(p["id"], "creativa"),
                 "progress": prog, "source": source}
        kind = OWNER_KIND.get(p["id"])
        if kind:
            objs = (items or {}).get(kind) or []
            entry["items"] = [_card(kind, o) for o in objs[:12]]
            entry["items_label"] = KIND_LABEL.get(kind, kind)
            entry["items_count"] = len(objs)
        out.append(entry)

    # phase pies = average progress of the personas in each phase
    phases = []
    for ph in PHASES:
        vals = [prog_by[i] for i in ph["ids"]]
        phases.append({**ph, "progress": _clamp(sum(vals) / max(1, len(vals)))})

    return {
        "stages": STAGES,
        "phases": phases,
        "personas": out,
        "overall": _clamp(sum(prog_by.values()) / max(1, len(prog_by))),
        "balls": _flow_balls(hyp, appr, exp, verdicts),
        "verdicts": (verdicts or [])[:6],
        "kpis": {"hypotheses": hyp, "approved": appr, "experiments": exp,
                 "real_experiments": real, "dossiers": doss, "papers": papers},
    }


def _flow_balls(hyp: int, appr: int, exp: int,
                verdicts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Each hypothesis is a 'ball' on the flow rail, placed in the phase it has reached.
    Distribution derived from real counts (verdicts→crítica, approved→investigación,
    the rest→creativa); the persona is a representative worker of that phase."""
    n = max(0, min(hyp, 9))
    if n == 0:
        return []
    done = min(n, len(verdicts or []) or min(exp, n))   # reached a verdict → crítica
    inv = min(n - done, max(0, appr - done))             # approved, en curso → investig.
    crea = n - done - inv
    worker = {"creativa": ["davinci", "kepler", "feynman", "hilbert"],
              "investig": ["hipatia", "tycho", "euler", "bohr"],
              "critica": ["popper", "godel", "euclides", "aristoteles"]}
    vlist = verdicts or []
    balls, i = [], 0
    plan = [("creativa", crea), ("investig", inv), ("critica", done)]
    for zone, cnt in plan:
        for j in range(cnt):
            v = vlist[i] if (zone == "critica" and i < len(vlist)) else {}
            balls.append({
                "id": f"H{i + 1}", "phase": zone,
                "persona": worker[zone][j % len(worker[zone])],
                "status": v.get("status") or ("good" if zone == "critica" else
                                              "warn" if zone == "investig" else "new"),
                "verdict": v.get("verdict") or v.get("label") or "",
            })
            i += 1
    return balls
