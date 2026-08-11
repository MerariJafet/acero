"""PRINCIPIO LEGO — las capacidades son piezas que se COMPONEN, no un pipeline fijo.

Visión de Merari (2026-08-11), protegida explícitamente contra la sobre-rigidez
que introduciría un PolicyEngine demasiado poderoso:

    CREATIVIDAD = ALTA.  AUTORIDAD EPISTÉMICA = BAJA.

Bohr debe poder pensar "este problema está en teoría de números, ¿pero qué pasa
si lo represento como matriz binaria primo×llave?" y de ahí saltar a álgebra
lineal, grafos bipartitos, set-cover o SAT. Nadie programa esa cadena: emerge
porque cada pieza declara QUÉ ACEPTA y QUÉ PRODUCE, y el sistema descubre las
composiciones compatibles.

Lo que este módulo NO hace: decidir qué ideas están permitidas. Eso sería
convertir la política en censor de creatividad — el error que este diseño evita
a propósito. El PolicyEngine administra ATENCIÓN y CÓMPUTO; las compuertas
epistémicas administran QUÉ PUEDE CREERSE. Imaginar es libre.

Lección que motiva `REPRESENTATION_SHIFT` como jugada de primera clase: la Ronda
4 de Erdős–Straus ejecutó correctamente muchas herramientas sobre una semántica
reducida — el problema no era la ejecución, era la MIRADA. Cambiar de
representación sin cambiar la premisa es una jugada legítima y hoy no existía.
"""

from __future__ import annotations

from typing import Any

# --- tipos de objeto que viajan entre piezas ---------------------------------------
# Deliberadamente pocos y generales: son los "conectores" del LEGO. Añadir un tipo
# nuevo es barato; lo caro sería que cada pieza hablara su propio dialecto.
OBJECT_TYPES = (
    "claim",            # un enunciado matemático/científico
    "sequence",         # a(1), a(2), … (p.ej. cover(N) por hitos)
    "tabular",          # filas numéricas (observaciones)
    "matrix",           # matriz numérica/binaria
    "graph",            # nodos + aristas
    "boolean_formula",  # restricciones SAT/SMT
    "set_system",       # familias de conjuntos (cover, hitting set)
    "pattern",          # PatternCandidate
    "hypothesis",       # conjetura falsable
    "rivals",           # teorías rivales competidoras
    "experiment_result",
    "counterexample",
    "lemma",
    "literature",
)

# --- catálogo de piezas: qué acepta / qué produce ----------------------------------
# `action` enlaza la pieza con la jugada de Bohr (None = pieza interna, alcanzable
# solo dentro de una composición). `evidence` es el kind del ledger que produce.
PIECES: dict[str, dict[str, Any]] = {
    "novelty_search": {
        "action": "hipatia", "accepts": ["claim", "hypothesis"],
        "produces": ["literature"], "evidence": "literature",
        "domain_tags": ["literatura"], "cost": "bajo", "llm_level": 1,
        "failure_modes": ["APIs caídas", "consulta mal formada"]},
    "counterexample_search": {
        "action": "popper", "accepts": ["claim", "hypothesis"],
        "produces": ["experiment_result", "counterexample"],
        "evidence": "experiment", "domain_tags": ["cómputo", "búsqueda"],
        "cost": "medio", "llm_level": 1,
        "failure_modes": ["espacio mal muestreado", "codegen roto"]},
    "smt_verification": {
        "action": "godel", "accepts": ["claim", "boolean_formula"],
        "produces": ["lemma"], "evidence": "lemma",
        "domain_tags": ["lógica", "SMT", "booleanos"], "cost": "alto",
        "llm_level": 0, "failure_modes": ["unknown por tiempo", "mala codificación"]},
    "symbolic_proof": {
        "action": None, "accepts": ["claim"], "produces": ["lemma"],
        "evidence": "lemma", "domain_tags": ["álgebra", "análisis"],
        "cost": "medio", "llm_level": 0,
        "failure_modes": ["sympy no decide"]},
    "pattern_discovery": {
        "action": "mendeleev", "accepts": ["tabular", "sequence", "matrix"],
        "produces": ["pattern"], "evidence": "pattern",
        "domain_tags": ["estadística", "simbólico", "secuencias"],
        "cost": "bajo", "llm_level": 0,
        "failure_modes": ["patrones triviales por construcción",
                          "falso descubrimiento por minería múltiple"]},
    "invariant_search": {
        "action": "mendeleev", "accepts": ["tabular", "matrix"],
        "produces": ["pattern"], "evidence": "pattern",
        "domain_tags": ["álgebra", "conservación"], "cost": "bajo",
        "llm_level": 0, "failure_modes": ["invariante de artefacto"]},
    "experiment_construction": {
        "action": "turing", "accepts": ["claim", "hypothesis", "pattern"],
        "produces": ["tabular", "matrix", "graph", "sequence",
                     "experiment_result"],
        "evidence": "build", "domain_tags": ["cómputo", "cualquiera"],
        "cost": "alto", "llm_level": 1,
        "failure_modes": ["presupuesto agotado", "pieza no instalable"]},
    "lateral_ideation": {
        "action": "ramanujan", "accepts": ["claim", "hypothesis"],
        "produces": ["hypothesis"], "evidence": "spark",
        "domain_tags": ["analogía", "cualquiera"], "cost": "bajo",
        "llm_level": 2, "failure_modes": ["idea no ejecutable"]},
    "representation_shift": {
        "action": "reinterpretar", "accepts": ["claim", "sequence", "tabular",
                                               "matrix", "graph", "set_system"],
        "produces": ["matrix", "graph", "boolean_formula", "set_system",
                     "sequence", "tabular"],
        "evidence": "representation", "domain_tags": ["cualquiera"],
        "cost": "bajo", "llm_level": 2,
        "failure_modes": ["transformación con pérdida no declarada"]},
    "rival_generation": {
        "action": "rivales", "accepts": ["pattern", "hypothesis"],
        "produces": ["rivals"], "evidence": "rival",
        "domain_tags": ["epistemología"], "cost": "bajo", "llm_level": 2,
        "failure_modes": ["rivales de paja"]},
    "discriminating_design": {
        "action": "discriminar", "accepts": ["rivals"],
        "produces": ["experiment_result"], "evidence": "experiment",
        "domain_tags": ["diseño experimental"], "cost": "medio",
        "llm_level": 1, "failure_modes": ["rivales predicen lo mismo"]},
    "adversarial_critique": {
        "action": "aristoteles", "accepts": ["claim", "pattern", "hypothesis",
                                             "experiment_result"],
        "produces": ["hypothesis"], "evidence": "critique",
        "domain_tags": ["epistemología"], "cost": "bajo", "llm_level": 2,
        "failure_modes": ["crítica genérica"]},
    "internal_refereeing": {
        "action": "noether", "accepts": ["lemma", "hypothesis"],
        "produces": ["hypothesis"], "evidence": "review",
        "domain_tags": ["epistemología"], "cost": "bajo", "llm_level": 2,
        "failure_modes": ["arbitraje complaciente"]},
    "result_interpretation": {
        "action": "feynman", "accepts": ["experiment_result", "pattern"],
        "produces": ["hypothesis", "claim"], "evidence": "reformulation",
        "domain_tags": ["cualquiera"], "cost": "bajo", "llm_level": 2,
        "failure_modes": ["reformulación que deriva de la premisa"]},
    "anomaly_harvest": {
        "action": "kepler", "accepts": ["experiment_result"],
        "produces": ["hypothesis"], "evidence": "candidate",
        "domain_tags": ["anomalías"], "cost": "bajo", "llm_level": 1,
        "failure_modes": ["ruido leído como anomalía"]},
    "dossier_packaging": {
        "action": "gauss", "accepts": ["lemma", "hypothesis", "pattern"],
        "produces": [], "evidence": "dossier", "domain_tags": ["publicación"],
        "cost": "bajo", "llm_level": 1,
        "failure_modes": ["empaquetar inmaduro"]},
}

# --- analogías: "esto se parece a…" (motor de Euler/Ramanujan) ----------------------
# NO son evidencia. Son puentes a representaciones donde hay OTRAS herramientas.
ANALOGIES: dict[str, list[dict[str, str]]] = {
    "set_system": [
        {"como": "set cover / hitting set", "habilita": "ILP, greedy con cota, "
         "dualidad LP", "tipo": "set_system"},
        {"como": "grafo bipartito objetos↔propiedades", "habilita":
         "comunidades, emparejamientos, nodos dominantes", "tipo": "graph"},
        {"como": "matriz binaria de incidencia", "habilita":
         "rango, valores singulares, clustering de filas/columnas",
         "tipo": "matrix"},
    ],
    "sequence": [
        {"como": "sistema dinámico discreto", "habilita":
         "puntos fijos, periodicidad, órbitas", "tipo": "sequence"},
        {"como": "función generatriz", "habilita":
         "álgebra de series, asintótica", "tipo": "claim"},
        {"como": "autómata / palabra sobre alfabeto", "habilita":
         "gramáticas, complejidad de descripción", "tipo": "boolean_formula"},
    ],
    "claim": [
        {"como": "restricciones booleanas", "habilita": "SAT/SMT, cube-and-conquer",
         "tipo": "boolean_formula"},
        {"como": "problema de optimización", "habilita": "ILP, relajaciones, cotas",
         "tipo": "set_system"},
        {"como": "clases de congruencia", "habilita":
         "CRT, proyección modular, conteo por clases", "tipo": "tabular"},
    ],
    "matrix": [
        {"como": "grafo (matriz de adyacencia/incidencia)", "habilita":
         "comunidades, motivos, espectro", "tipo": "graph"},
        {"como": "código lineal", "habilita": "distancia mínima, síndromes",
         "tipo": "matrix"},
    ],
    "graph": [
        {"como": "matriz de adyacencia", "habilita":
         "álgebra lineal, espectro, bajo rango", "tipo": "matrix"},
        {"como": "instancia de cobertura", "habilita": "set cover, dominación",
         "tipo": "set_system"},
    ],
    "tabular": [
        {"como": "nube de puntos en espacio de features", "habilita":
         "geometría, dimensión intrínseca, clusters", "tipo": "matrix"},
        {"como": "distribución empírica", "habilita":
         "entropía, información mutua, nulos", "tipo": "tabular"},
    ],
}


def pieces_accepting(object_type: str) -> list[str]:
    """¿Qué piezas pueden trabajar con este tipo de objeto? (la pregunta LEGO)."""
    return sorted(n for n, p in PIECES.items()
                  if object_type in (p.get("accepts") or []))


def compositions_from(object_type: str, *, depth: int = 3,
                      max_chains: int = 40) -> list[list[str]]:
    """Cadenas de piezas COMPATIBLES a partir de un tipo de objeto.

    Esto es lo que convierte al TOOLBOX en LEGO: nadie programó
    "sequence→matrix→graph→comunidades"; emerge de los conectores. Bohr recibe
    estas cadenas como MENÚ DE IDEAS, no como plan obligatorio — decide él."""
    chains: list[list[str]] = []

    def walk(current: str, path: list[str], seen: set[str]) -> None:
        if len(chains) >= max_chains or len(path) >= depth:
            return
        for name in pieces_accepting(current):
            if name in seen:            # sin ciclos: una pieza por cadena
                continue
            new_path = path + [name]
            chains.append(new_path)
            for out_type in (PIECES[name].get("produces") or []):
                walk(out_type, new_path, seen | {name})

    walk(object_type, [], set())
    return chains[:max_chains]


def analogies_for(object_type: str) -> list[dict[str, str]]:
    """"Esto se parece a…" — puentes a otras representaciones. NO es evidencia:
    genera representación candidata + método candidato + experimento barato."""
    return list(ANALOGIES.get(object_type, []))


def lego_context(object_type: str = "claim", *, depth: int = 2) -> str:
    """El bloque que Bohr lee para pensar en LEGO: qué piezas aceptan lo que
    tiene, a qué se parece, y qué composiciones son compatibles."""
    lines = [f"PIEZAS LEGO disponibles para un objeto de tipo '{object_type}':"]
    for name in pieces_accepting(object_type):
        p = PIECES[name]
        act = p.get("action") or "(interna)"
        lines.append(f"  - {name} [jugada: {act}] produce "
                     f"{', '.join(p.get('produces') or []) or '—'} "
                     f"· costo {p.get('cost')} · {', '.join(p.get('domain_tags', []))}")
    ana = analogies_for(object_type)
    if ana:
        lines.append(f"\nANALOGÍAS ('{object_type}' se parece a…) — puentes a otras "
                     "herramientas, NO evidencia:")
        for a in ana:
            lines.append(f"  - {a['como']} → habilita {a['habilita']} "
                         f"(tipo destino: {a['tipo']})")
    comps = [c for c in compositions_from(object_type, depth=depth) if len(c) >= 2]
    if comps:
        lines.append("\nCOMPOSICIONES COMPATIBLES (ejemplos, NO obligatorias):")
        for c in comps[:8]:
            lines.append("  - " + " → ".join(c))
    lines.append("\nPuedes INVENTAR composiciones que no estén aquí si los tipos "
                 "encajan. Cambiar de representación NO cambia la premisa sellada: "
                 "si una transformación pierde información, decláralo.")
    return "\n".join(lines)


def validate_pieces() -> list[str]:
    """Invariantes del LEGO (CI): tipos declarados válidos y sin piezas mudas."""
    errors = []
    for name, p in PIECES.items():
        for t in (p.get("accepts") or []) + (p.get("produces") or []):
            if t not in OBJECT_TYPES:
                errors.append(f"pieza '{name}': tipo '{t}' no está en OBJECT_TYPES")
        if not p.get("accepts"):
            errors.append(f"pieza '{name}' no acepta nada — inalcanzable")
        if not p.get("failure_modes"):
            errors.append(f"pieza '{name}' no declara modos de fallo")
    for t, lst in ANALOGIES.items():
        if t not in OBJECT_TYPES:
            errors.append(f"analogía sobre tipo desconocido '{t}'")
        for a in lst:
            if a.get("tipo") not in OBJECT_TYPES:
                errors.append(f"analogía '{a.get('como')}' apunta a tipo inválido")
    return errors
