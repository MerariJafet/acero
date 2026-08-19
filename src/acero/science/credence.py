"""Credence — incertidumbre explícita por hipótesis, calculada del ledger.

Crítica del revisor externo (2026-08-10), aceptada: los estados categóricos
(partial_progress, refuted…) sirven al workflow pero no distinguen "no tengo
evidencia" de "tengo evidencia en contra" de "tengo evidencia favorable débil"
de "evidencia fuerte pero solo en una región".

Esto NO es bayesianismo estricto: es un resumen MECÁNICO y auditable derivado de
las filas del ledger (nunca de texto de LLM), con la fórmula a la vista. La
credence resultante es una heurística DECLARADA como heurística — su valor está
en separar los cuatro casos de arriba, no en fingir probabilidades calibradas.
"""

from __future__ import annotations

import re
from typing import Any

_ESPACIOS = re.compile(r"\s+")


def _norm(texto: Any) -> str:
    """Normaliza texto para comparar contenido: minúsculas y espacios colapsados.
    Deliberadamente simple -- no queremos un dedup 'inteligente' que junte dos
    resultados genuinamente distintos por parecerse."""
    return _ESPACIOS.sub(" ", str(texto or "").strip().lower())


def _huella(kind: str, payload: dict[str, Any]) -> str:
    """Huella de CONTENIDO de una pieza de evidencia.

    Dos filas con la misma huella son la MISMA evidencia, aunque sean filas
    distintas del ledger (reintento tras un fallo de procedencia, doble registro,
    re-corrida idéntica). La iteración 10 del meta-supervisor demostró con números
    reales que sin esto, 2 lemas idénticos + 4 experimentos idénticos daban el
    mismo credence 0.95 que evidencia genuinamente diversa.

    Para experimentos la huella incluye el veredicto: el mismo claim probado y
    REFUTADO es evidencia distinta del mismo claim probado y sostenido."""
    if kind == "lemma":
        return "lemma|" + _norm(payload.get("statement") or payload.get("claim"))
    if kind == "experiment":
        verdict = _norm((payload.get("result") or {}).get("verdict")
                        or payload.get("verdict"))
        claim = _norm(payload.get("claim") or payload.get("statement")
                      or payload.get("hypothesis"))
        return f"experiment|{claim}|{verdict}"
    if kind == "negative":
        return "negative|" + _norm(payload.get("statement") or payload.get("claim"))
    if kind == "pattern":
        return "pattern|" + _norm(payload.get("expr") or payload.get("description")
                                  or payload.get("statement"))
    return kind + "|" + _norm(payload.get("statement"))


def credence_for(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Resumen de incertidumbre a partir de las filas crudas del ledger de UNA
    hipótesis (list_rows filtradas por parent_id o proyecto completo).

    Señales (todas mecánicas):
      + lemma proved (backend mecánico)      → evidencia fuerte a favor
      + experiment holds_empirically         → favorable débil
      + pattern con ≥2 vistas independientes → favorable débil (estructura)
      − negative / refuted                   → evidencia en contra
      ± critique/review con objeciones       → resta confianza, no evidencia

    DEDUPLICACIÓN (2026-08-19): evidencia repetida o dependiente NO cuenta como
    evidencia independiente. Se descarta en dos niveles, ambos mecánicos:
      1. por `id` de fila -- la misma fila listada dos veces cuenta una vez;
      2. por HUELLA DE CONTENIDO (`_huella`) -- dos filas distintas que dicen lo
         mismo son la misma evidencia.
    El resultado incluye `duplicados_descartados` para que la deduplicación sea
    auditable y no una caja negra."""
    a_favor_fuerte = a_favor_debil = en_contra = objeciones = 0
    dominio: list[str] = []
    ids_vistos: set[Any] = set()
    huellas_vistas: set[str] = set()
    duplicados = {"por_id": 0, "por_contenido": 0}

    for r in rows:
        rid = r.get("id")
        if rid is not None:
            if rid in ids_vistos:
                duplicados["por_id"] += 1
                continue
            ids_vistos.add(rid)

        kind = str(r.get("kind") or "")
        p = r.get("payload") or {}

        # las críticas no son evidencia: sus objeciones se acumulan aunque el
        # texto se repita (dos revisores señalando lo mismo sí es señal doble de
        # que el punto flojo existe). No entran al dedup de evidencia.
        if kind in ("critique", "review"):
            objs = (p.get("objections") or p.get("objeciones_mayores") or [])
            objeciones += len(objs)
            continue

        huella = _huella(kind, p)
        if huella in huellas_vistas:
            duplicados["por_contenido"] += 1
            continue
        huellas_vistas.add(huella)

        if kind == "lemma" and p.get("proved"):
            a_favor_fuerte += 1
        elif kind == "experiment":
            verdict = str((p.get("result") or {}).get("verdict")
                          or p.get("verdict") or "")
            if "refut" in verdict:
                en_contra += 1
            elif "holds" in verdict or "verified" in verdict:
                a_favor_debil += 1
            n_tested = (p.get("result") or {}).get("n_tested") or p.get("n_tested")
            if n_tested:
                dominio.append(f"n={n_tested}")
        elif kind == "negative":
            en_contra += 1
        elif kind == "pattern" and int(p.get("independent_views") or 1) >= 2:
            a_favor_debil += 1
    # heurística DECLARADA: base 0.5, evidencia mueve, objeciones descuentan.
    # saturación suave para que 100 experimentos no den certeza (no la dan).
    raw = (0.5 + 0.18 * min(a_favor_fuerte, 2) + 0.05 * min(a_favor_debil, 4)
           - 0.30 * min(en_contra, 2) - 0.02 * min(objeciones, 5))
    credence = round(max(0.02, min(0.95, raw)), 2)
    if en_contra and not (a_favor_fuerte or a_favor_debil):
        estado = "evidencia EN CONTRA"
    elif not (en_contra or a_favor_fuerte or a_favor_debil):
        estado = "SIN evidencia (no confundir con evidencia en contra)"
    elif a_favor_fuerte:
        estado = ("evidencia fuerte a favor"
                  + (f" — pero SOLO en {dominio[-1]}" if dominio else "")
                  + ("; hay contraevidencia" if en_contra else ""))
    else:
        estado = ("evidencia favorable débil"
                  + ("; hay contraevidencia" if en_contra else ""))
    return {"credence": credence, "estado": estado,
            "a_favor_fuerte": a_favor_fuerte, "a_favor_debil": a_favor_debil,
            "en_contra": en_contra, "objeciones": objeciones,
            "dominio_probado": dominio[-1] if dominio else "no cuantificado",
            "duplicados_descartados": duplicados,
            "formula": "0.5 +0.18·min(fuerte,2) +0.05·min(débil,4) "
                       "−0.30·min(contra,2) −0.02·min(objeciones,5) "
                       "sobre evidencia DEDUPLICADA por id y por huella de "
                       "contenido (heurística mecánica declarada, no "
                       "probabilidad calibrada)"}


def render_line(c: dict[str, Any]) -> str:
    return (f"credence {c['credence']:.2f} — {c['estado']} "
            f"[fuerte:{c['a_favor_fuerte']} débil:{c['a_favor_debil']} "
            f"contra:{c['en_contra']} obj:{c['objeciones']} "
            f"dominio:{c['dominio_probado']}]")
