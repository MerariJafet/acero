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

STAGES = [
    {"key": "plantear", "name": "Plantear", "ids": ["hilbert", "euler", "hipatia"]},
    {"key": "explorar", "name": "Explorar / crear",
     "ids": ["arquimedes", "davinci", "kepler", "tycho", "ramanujan", "turing"]},
    {"key": "confrontar", "name": "Confrontar",
     "ids": ["popper", "euclides", "godel", "aristoteles"]},
    {"key": "segunda", "name": "Segunda jugada", "ids": ["feynman", "bohr"]},
    {"key": "publicar", "name": "Publicar", "ids": ["gauss"]},
]

# the 3 macro-phases (the pies) and which persona lives in each
PHASES = [
    {"key": "creativa", "name": "Fase Creativa", "sub": "idear · plantear · explorar",
     "ids": ["hilbert", "arquimedes", "davinci", "kepler", "feynman",
             "ramanujan", "turing"]},
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
    {"id": "kepler", "name": "Kepler", "role": "Sintetiza + cosecha anomalías",
     "module": "_synthesize + anomalies.py", "status": "warn", "hands_to": "Popper",
     "awaits": "Da Vinci / Tycho",
     "summary": "Destila leyes precisas y, como hizo con los datos de Tycho, convierte "
                "cada discrepancia medida en una hipótesis NUEVA (🔥 anomalías).",
     "face": {"hair": "short", "beard": "mous", "hairc": "#cbb89c", "hat": "ruff"},
     "tasks": [["Destilar hipótesis", "done"], ["Cosechar anomalías", "done"],
               ["Forma formal fiable", "doing"]]},
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
    {"id": "ramanujan", "name": "Ramanujan", "role": "La chispa en la frontera (¿y si…?)",
     "module": "spark.py", "status": "new", "hands_to": "Turing", "awaits": "Bohr",
     "summary": "Cuando el problema dice 'no se puede', él pregunta ¿y si sí? — ideas "
                "laterales, analogías entre ramas, probabilidad honesta y el primer "
                "experimento barato que las mata o las aviva.",
     "face": {"hair": "short", "hairc": "#1d1712", "skin": 4},
     "tasks": [["Leer el TOOLBOX (LEGO)", "done"], ["Chispas con probabilidad", "done"],
               ["Rodaje en fronteras reales", "doing"]]},
    {"id": "turing", "name": "Turing", "role": "Construye y corre lo que haga falta",
     "module": "turing.py + toolbox.py", "status": "new",
     "hands_to": "Gödel / Aristóteles", "awaits": "Ramanujan",
     "summary": "El matemático que programa: escribe el experimento en Python, instala "
                "piezas faltantes (pip/docker, Sage incluido) o las construye, repara "
                "sus errores y reintenta con presupuesto de HORAS.",
     "face": {"hair": "side", "hairc": "#2c231b", "skin": 1},
     "tasks": [["Codegen + sandbox + repair", "done"], ["ensure() de piezas", "done"],
               ["Sage jaulado (docker)", "done"]]},
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
    "ramanujan": {"hair": "short", "hairc": "#141010", "skin": 4, "browc": "#141010",
                  "accent": "#e8b23c"},
    "turing": {"hair": "side", "hairc": "#2c231b", "skin": 1, "browc": "#2c231b",
               "accent": "#4c8fd6"},
}
for _p in PERSONAS:
    _p["face"] = _FACES.get(_p["id"], _p.get("face", {}))


def _clamp(x: float) -> int:
    return max(0, min(100, int(round(x))))


# qué "kind" del ledger es dueño cada personaje → sus fichas reales
OWNER_KIND = {"hilbert": "candidate", "hipatia": "literature", "popper": "experiment",
              "gauss": "dossier", "aristoteles": "critique",
              "feynman": "reformulation", "godel": "lemma", "bohr": "decision",
              "ramanujan": "spark", "turing": "build"}
KIND_LABEL = {"candidate": "hipótesis", "literature": "literatura",
              "experiment": "experimentos", "dossier": "dossiers", "critique": "objeciones",
              "reformulation": "reformulaciones", "lemma": "lemas y cotas",
              "decision": "decisiones de orquestación",
              "spark": "chispas (¿y si…?)", "build": "experimentos construidos"}


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
    if kind == "decision":
        return {"title": (o.get("reason") or "decisión")[:140],
                "verdict": f"→ {o.get('to') or '?'}", "by": "Bohr"}
    if kind == "candidate":
        return {"title": (o.get("claim") or o.get("statement") or "hipótesis")[:140],
                "verdict": o.get("status") or "", "by": o.get("by") or ""}
    if kind == "dossier":
        return {"title": (o.get("synthesis") or o.get("claim") or "dossier")[:140],
                "verdict": o.get("readiness") or "", "by": ""}
    if kind == "literature":
        return {"title": (o.get("title") or o.get("claim") or "referencia")[:140],
                "verdict": str(o.get("year") or ""), "by": ""}
    if kind == "spark":
        prob = o.get("probabilidad")
        return {"title": (o.get("chispa") or "chispa")[:140],
                "verdict": (f"p={prob}" if prob is not None else "idea"),
                "by": (o.get("analogia") or "")[:60]}
    if kind == "build":
        return {"title": (o.get("verdict") or o.get("idea") or "experimento")[:140],
                "verdict": o.get("status") or "", "by": "Turing"}
    return {"title": (o.get("summary") or o.get("claim") or o.get("title") or "—")[:140],
            "verdict": o.get("status") or "", "by": ""}


# qué personaje ejecuta cada tipo de evento del ledger (para el rastreo del flujo)
KIND_PERSONA = {"candidate": "hilbert", "literature": "hipatia", "experiment": "popper",
                "reformulation": "feynman", "lemma": "godel", "negative": "popper",
                "critique": "aristoteles", "dossier": "gauss",
                "spark": "ramanujan", "build": "turing"}
KIND_STEP = {"candidate": "planteó", "literature": "buscó literatura",
             "experiment": "corrió experimento", "reformulation": "reformuló",
             "lemma": "probó lema/cota", "negative": "halló contraejemplo",
             "critique": "objetó", "dossier": "empaquetó",
             "spark": "lanzó una chispa", "build": "construyó y corrió"}
_NAME_TO_ID = {p["name"].lower(): p["id"] for p in PERSONAS}


def _next_of(pid: str) -> str | None:
    """A quién le pasará la info `pid` (primer nombre válido de su hands_to)."""
    persona = next((p for p in PERSONAS if p["id"] == pid), None)
    for token in str((persona or {}).get("hands_to") or "").split("/"):
        nid = _NAME_TO_ID.get(token.strip().lower())
        if nid:
            return nid
    return None


def build_flows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-hypothesis flow columns from the raw ledger rows (ULID ids ⇒ id order is
    chronological): H1, H2… each with the ordered chain of personas who worked it,
    who has it NOW, where it CAME from and where it will GO next."""
    # ojo: el orden temporal vive en el ULID DESPUÉS del prefijo (hyp_/exp_/lit_…);
    # ordenar por id completo mezclaría por tipo, no por tiempo.
    rows = sorted(rows or [], key=lambda r: str(r.get("id") or "").split("_", 1)[-1])
    hyps = [r for r in rows if r.get("kind") == "candidate"]
    flows = []
    for i, h in enumerate(hyps):
        pay = h.get("payload") or {}
        steps = [{"persona": (pay.get("by") if pay.get("by") in KIND_PERSONA.values()
                              or pay.get("by") in [p["id"] for p in PERSONAS]
                              else "hilbert"),
                  "kind": "candidate", "did": KIND_STEP["candidate"]}]
        for r in rows:
            if r.get("parent_id") != h.get("id"):
                continue
            k = str(r.get("kind") or "")
            pid = ((r.get("payload") or {}).get("by")
                   or KIND_PERSONA.get(k))
            if not pid or pid not in [p["id"] for p in PERSONAS]:
                pid = KIND_PERSONA.get(k)
            if not pid:
                continue
            v = ((r.get("payload") or {}).get("result") or {}).get("verdict") or ""
            steps.append({"persona": pid, "kind": k,
                          "did": KIND_STEP.get(k, k), "verdict": v})
        # colapsar pasos CONSECUTIVOS del mismo personaje+acción (p.ej. Hipatia
        # registró 12 papers → UN paso "buscó literatura ×12", no 12 caritas)
        collapsed: list[dict[str, Any]] = []
        for s in steps:
            prev_s = collapsed[-1] if collapsed else None
            if (prev_s and prev_s["persona"] == s["persona"]
                    and prev_s["kind"] == s["kind"]):
                prev_s["n"] = int(prev_s.get("n", 1)) + 1
                if s.get("verdict"):
                    prev_s["verdict"] = s["verdict"]
            else:
                collapsed.append({**s, "n": 1})
        steps = collapsed
        cur = steps[-1]["persona"]
        prev = next((s["persona"] for s in reversed(steps[:-1])
                     if s["persona"] != cur), None)
        # estado de la columna: 'closed' = terminada, nada pendiente (gris);
        # 'open' = aún tiene algo que decir → espera una decisión (sombra roja)
        status = str(h.get("status") or "").upper()
        last_v = str(steps[-1].get("verdict") or "")
        closed = (status in ("REJECTED", "CLOSED", "ARCHIVED")
                  or last_v in ("verified", "refuted"))
        flows.append({
            "id": pay.get("tag") or f"H{i + 1}", "hid": h.get("id"),
            "title": (pay.get("title") or pay.get("claim")
                      or pay.get("description") or "")[:120],
            "status": h.get("status") or "",
            "state": "closed" if closed else "open",
            "steps": steps, "current": cur, "from": prev, "next": _next_of(cur),
        })
    return flows


def _journey(k: dict[str, Any], items: dict[str, list[dict[str, Any]]],
             live: dict[str, Any] | None) -> dict[str, Any]:
    """El VIAJE de la investigación: hitos reales cumplidos → % general + qué sigue.
    Honesto: cada hito se marca solo con evidencia en el ledger; el último (validación
    externa humana) nunca lo marca la máquina."""
    it = items or {}
    exps = it.get("experiment") or []
    lems = it.get("lemma") or []
    has_verdict = any(((e.get("result") or {}).get("verdict") or "") for e in exps)
    milestones = [
        ("Conjetura planteada (Hilbert)", int(k.get("hypotheses") or 0) > 0, 15),
        ("Novedad/literatura (Hipatia)",
         int(k.get("papers") or 0) > 0 or bool(it.get("literature")), 10),
        ("Atacada computacionalmente (Popper)", len(exps) > 0, 15),
        ("Con veredicto honesto", has_verdict, 15),
        ("Segunda jugada (Feynman/Gödel)",
         bool(it.get("reformulation")) or bool(lems), 15),
        ("Lema/contribución PROBADA", any(bool(x.get("proved")) for x in lems), 15),
        ("Dossier empaquetado (Gauss)", int(k.get("dossiers") or 0) > 0, 10),
        ("Validación externa HUMANA", False, 5),   # siempre la marca un humano, no ACERO
    ]
    pct = sum(w for _, done, w in milestones if done)
    nxt = next((label for label, done, _ in milestones if not done), None)
    if live and not live.get("done"):
        nxt = f"en curso: {live.get('label') or 'el Consejo trabaja'}"

    # 🧭 FRONTERA: qué tan cerca estamos de conocimiento de frontera / NUEVO — honesto,
    # derivado de la novedad (Hipatia) y de la disposición del último ciclo.
    cands = it.get("candidate") or []
    nv = next((str((c.get("novelty") or {}).get("status") or "")
               for c in reversed(cands) if (c.get("novelty") or {}).get("status")), "")
    disp = str((live or {}).get("disposition") or "")
    if nv == "asentada":
        frontier = {"level": "detras",
                    "label": "DETRÁS de la frontera: esto ya se sabe en la literatura — "
                             "el valor ahora es APRENDERLO y reproducirlo con rigor, "
                             "no descubrirlo."}
    elif disp in ("verified", "partial_progress", "formally_supported"):
        frontier = {"level": "tocando",
                    "label": "TOCANDO la frontera: hay un pedazo demostrado "
                             "mecánicamente sobre una pregunta no resuelta directa — si "
                             "sobrevive a la revisión humana, sería conocimiento NUEVO."}
    elif nv == "abierta":
        frontier = {"level": "en",
                    "label": "EN la frontera: pregunta probablemente ABIERTA; "
                             "sobrevivir búsquedas no basta — el paso a conocimiento "
                             "nuevo exige demostración o evidencia decisiva + humanos."}
    else:
        frontier = {"level": "camino",
                    "label": "EN CAMINO a la frontera: aún estamos clasificando si la "
                             "pregunta es nueva o ya está resuelta (falta la lectura "
                             "de Hipatia o un ciclo completo)."}
    return {"pct": _clamp(pct),
            "next_step": nxt or "todo listo — falta la revisión humana",
            "frontier": frontier,
            "milestones": [{"label": lb, "done": bool(d)} for lb, d, _ in milestones]}


_NAME_OF = {p["id"]: p["name"] for p in PERSONAS}


def _story_line(step: dict[str, Any], nxt: str | None) -> str:
    """Un párrafo en PRIMERA PERSONA y PEDAGÓGICO: qué hice, CÓMO, POR QUÉ y qué
    SIGNIFICA — el Consejo también enseña. Determinista: sale del ledger."""
    k, v, n = step.get("kind"), step.get("verdict") or "", int(step.get("n") or 1)
    txt = {
        "candidate":
            "planteé la conjetura como afirmación FALSABLE. ¿Cómo? Exigiendo "
            "cuantificadores y condiciones explícitas, para que un solo contraejemplo "
            "pueda tumbarla. ¿Por qué? Sin falsabilidad no hay ciencia, solo opinión. "
            "Significa: ya tenemos un blanco preciso al que disparar",
        "literature":
            f"leí {n} fuente(s) reales (OpenAlex/arXiv/Crossref) buscando si ya estaba "
            "resuelta. ¿Cómo? Redactando consultas de experto y cruzando fuentes. "
            "¿Por qué? Gastar cómputo en algo ya resuelto no es descubrir, es recuperar "
            "(el error 'Erdősgate'). Significa: sabemos si pisamos terreno nuevo o "
            "terreno de libro de texto",
        "experiment":
            f"la ataqué computacionalmente ({n} corrida(s)"
            + (f", veredicto: {v}" if v else "") + "). ¿Cómo? Generé programas que "
            "barren miles de casos buscando UN contraejemplo, con guardas contra "
            "falsos positivos numéricos. ¿Por qué? Refutar rápido y barato antes de "
            "intentar demostrar. Significa: "
            + ("encontré un caso donde FALLA — la versión actual es falsa"
               if v == "refuted" else
               "sobrevivió a todo lo que le lancé — pero pasar pruebas NO es demostrar"
               if v == "holds_empirically" else
               "el ataque no concluyó: ni la tumbé ni la confirmé"),
        "negative":
            "registré el contraejemplo como resultado NEGATIVO permanente. ¿Por qué? "
            "Los fracasos documentados evitan repetir callejones y delimitan dónde la "
            "idea NO funciona. Significa: el mapa de lo falso también es conocimiento",
        "reformulation":
            "observé que el fallo era un BORDE (un caso degenerado o ruido numérico), "
            f"no el núcleo de la idea, y reformulé el enunciado"
            f"{' ×' + str(n) if n > 1 else ''}. ¿Cómo? Excluyendo el borde y afilando "
            "cuantificadores/regímenes. ¿Por qué? Un investigador de verdad hace la "
            "SEGUNDA jugada en vez de rendirse. Significa: la conjetura sale más "
            "fuerte de cada refutación superficial",
        "lemma":
            "intenté DEMOSTRARLA con motores formales (sympy/Z3) y dejé un lema o cota"
            + (f" ({v})" if v else "") + ". ¿Cómo? Reduciendo el argumento a un núcleo "
            "que la máquina pueda verificar símbolo a símbolo. ¿Por qué? Demostrar > "
            "comprobar: una prueba cubre infinitos casos de golpe. Significa: "
            + ("un pedazo del argumento quedó PROBADO mecánicamente"
               if v == "probado" else
               "el pedazo quedó propuesto; aún nadie lo probó"),
        "critique":
            "la sometí a revisión HOSTIL" + (f": veredicto {v}" if v else "") + ". "
            "¿Cómo? Buscando la afirmación exacta, alternativas no descartadas y qué "
            "la falsaría. ¿Por qué? Si nosotros no la rompemos, lo hará el primer "
            "revisor externo. Significa: conocemos sus puntos débiles ANTES de "
            "presumirla",
        "dossier":
            "empaqueté el dossier con evidencia y límites explícitos. ¿Por qué? Nada "
            "se publica solo: el techo de ACERO es 'listo para revisión humana'. "
            "Significa: te toca a ti decidir si esto avanza",
        "spark":
            f"lancé {n} chispa(s) en la frontera: donde el problema dice 'no se "
            "puede', yo pregunto ¿y si sí? ¿Cómo? Leyendo el catálogo de piezas "
            "(LEGO) y buscando analogías laterales — el clásico '¿y si mejor usamos "
            "matrices?'. ¿Por qué? Los métodos directos ya se agotaron ahí. "
            "Significa: hay ideas nuevas sobre la mesa, cada una con su apuesta "
            "honesta y su experimento barato",
        "build":
            "construí y corrí el experimento de la chispa: escribí el código, leí "
            "mis errores, los reparé y reintenté. ¿Cómo? Con las piezas que me "
            "eligieron (instalando las faltantes — Sage incluido) y aritmética "
            "exacta. ¿Por qué? Una idea sin experimento es solo poesía. Significa: "
            "la chispa ya tiene evidencia a favor o en contra — nunca un teorema "
            "hasta que Gödel y Aristóteles la pasen",
    }.get(k, step.get("did") or str(k))
    if nxt:
        txt += f". Se la pasé a {_NAME_OF.get(nxt, nxt)}"
    return txt


def build_stories(flows: list[dict[str, Any]] | None) -> dict[str, list[str]]:
    """Por personaje: 'mi trabajo, hipótesis por hipótesis' — H1: hice X; se la pasé a Y."""
    out: dict[str, list[str]] = {}
    for f in flows or []:
        steps = f.get("steps") or []
        for i, s in enumerate(steps):
            nxt = steps[i + 1]["persona"] if i + 1 < len(steps) else None
            nxt = nxt if nxt != s["persona"] else None
            line = f"{f.get('id')}: {_story_line(s, nxt)}."
            out.setdefault(s["persona"], []).append(line)
    return out


def council_for(kpis: dict[str, Any] | None,
                verdicts: list[dict[str, Any]] | None = None,
                items: dict[str, list[dict[str, Any]]] | None = None,
                flows: list[dict[str, Any]] | None = None,
                live: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble the council for one project from its real KPIs."""
    k = kpis or {}
    hyp = int(k.get("hypotheses") or 0)
    appr = int(k.get("approved") or 0)
    exp = int(k.get("experiments") or 0)
    doss = int(k.get("dossiers") or 0)
    papers = int(k.get("papers") or 0)
    it = items or {}

    def _n(kind: str) -> int:
        return len(it.get(kind) or [])
    lit_n, ref_n, lem_n, crit_n = (_n("literature"), _n("reformulation"),
                                   _n("lemma"), _n("critique"))

    # PROGRESO = trabajo REAL hecho en ESTE proyecto → 0 si nadie ha participado aún.
    # La MADUREZ de la capacidad (bueno/mejorable/nuevo/débil) NO es progreso: vive en el
    # color del estado del personaje, no en el anillo. Así una investigación recién creada
    # arranca en 0% y el anillo se llena solo cuando cada personaje deja fichas reales.
    project_signal = {
        "hilbert": hyp * 20,
        "euler": hyp * 12,
        "hipatia": max(papers, lit_n) * 20,
        "arquimedes": 0,                       # catálogo: capacidad, no avance por-proyecto
        "davinci": exp * 16,
        "kepler": appr * 20,
        "tycho": (exp + appr) * 10,
        "popper": exp * 16,
        "euclides": lem_n * 20,
        "godel": lem_n * 20,
        "aristoteles": crit_n * 20,
        "feynman": ref_n * 20,
        "bohr": (hyp + exp + appr + doss) * 8,
        "gauss": (doss + papers) * 24,
    }

    stories = build_stories(flows)
    out = []
    prog_by = {}
    for p in PERSONAS:
        prog = _clamp(project_signal.get(p["id"], 0))
        source = "project" if prog > 0 else "idle"
        prog_by[p["id"]] = prog
        entry = {**p, "phase": _PHASE_OF.get(p["id"], "creativa"),
                 "progress": prog, "source": source,
                 "story": (stories.get(p["id"]) or [])[:10]}
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

    # halos: verde = trabaja AHORA, amarillo = de dónde VIENE, naranja = a dónde VA.
    # Si el ciclo está EN VIVO, manda el estado en vivo; si no, el último paso de cada H.
    halo_now: set[str] = set()
    halo_from: set[str] = set()
    halo_next: set[str] = set()
    if live and not live.get("done"):
        halo_now = {str(live.get("persona") or "")} - {""}
        halo_from = {str(live.get("from_persona") or "")} - {""}
        halo_next = {str(live.get("next_persona") or "")} - {""}
    else:
        for f in flows or []:
            if f.get("current"):
                halo_now.add(f["current"])
            if f.get("from"):
                halo_from.add(f["from"])
            if f.get("next"):
                halo_next.add(f["next"])
    halo_from -= halo_now
    halo_next -= halo_now | halo_from

    return {
        "stages": STAGES,
        "phases": phases,
        "personas": out,
        "overall": _clamp(sum(prog_by.values()) / max(1, len(prog_by))),
        "journey": _journey(k, items or {}, live),
        "balls": _flow_balls(hyp, appr, exp, verdicts),
        "flows": flows or [],
        "live": live,
        "halos": {"now": sorted(halo_now), "from": sorted(halo_from),
                  "next": sorted(halo_next)},
        "verdicts": (verdicts or [])[:6],
        "kpis": {"hypotheses": hyp, "approved": appr, "experiments": exp,
                 "real_experiments": int(k.get("real_experiments") or 0),
                 "dossiers": doss, "papers": papers},
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
