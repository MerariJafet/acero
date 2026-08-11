"""Permisos de estado — quién puede escribir qué al ledger, a nivel de TIPOS.

Crítica del revisor externo (2026-08-10), aceptada: muchos nombres epistemológicos
producen ilusión de rigor si al final cualquier módulo puede escribir cualquier
cosa. Estas reglas son MECÁNICAS (no prompt):

  * Cada `kind` de evidencia tiene actores autorizados. Noether jamás escribe un
    lemma; Bohr jamás escribe un pattern; nadie suplanta a nadie.
  * Un `lemma` con proved=True exige backend MECÁNICO declarado (sympy/z3/…).
    El texto de un LLM no puede convertirse en prueba por ningún camino.
  * Violación ⇒ la escritura se DEGRADA (payload marcado, proved forzado a
    False, estado FLAGGED) y queda registrada — jamás se pierde información,
    jamás se eleva de más. Degradar es honesto; bloquear escondería el intento.
"""

from __future__ import annotations

from typing import Any

# kind → actores autorizados a escribirlo (None = cualquiera: kinds operativos)
KIND_WRITERS: dict[str, set[str] | None] = {
    "candidate": {"Hilbert", "Kepler", "Bohr"},
    "literature": {"Hipatia"},
    "experiment": {"Popper", "Da Vinci"},
    "negative": {"Popper"},
    "lemma": {"Gödel", "Euclides"},
    "critique": {"Aristóteles"},
    "reformulation": {"Feynman"},
    "decision": {"Bohr"},
    "spark": {"Ramanujan"},
    "build": {"Turing"},
    "review": {"Noether"},
    "pattern": {"Mendeleev"},
    "dossier": {"Gauss"},
    "premise": {"Hilbert"},
    "drift": {"Hilbert"},
    "suggestion": {"Bohr"},
    "report": {"Bohr"},
    "council_status": None,
    "session": None,
    "violation": None,      # evento de seguridad epistémica: lo escribe el sistema
}

# backends que cuentan como prueba MECÁNICA (para lemma.proved=True)
MECHANICAL_BACKENDS = {"sympy", "z3", "sympy/z3", "lean", "flint", "pari"}


def check_put(actor: str, kind: str, payload: dict[str, Any]
              ) -> tuple[dict[str, Any], list[str]]:
    """Valida una escritura. → (payload posiblemente DEGRADADO, violaciones).

    Nunca lanza y nunca descarta datos: si hay violación, el payload se marca
    (`_permiso_violado`) y las elevaciones indebidas se revierten (proved=False).
    """
    violations: list[str] = []
    out = dict(payload or {})
    writers = KIND_WRITERS.get(kind, None)
    if writers is not None and actor not in writers:
        violations.append(f"actor '{actor}' no está autorizado a escribir "
                          f"kind='{kind}' (autorizados: {sorted(writers)})")
    if kind == "lemma" and out.get("proved"):
        backend = str(out.get("backend") or "").lower()
        if not any(b in backend for b in MECHANICAL_BACKENDS):
            violations.append("lemma con proved=True sin backend mecánico "
                              f"({backend!r}) — texto de LLM no es prueba; "
                              "degradado a proved=False")
            out["proved"] = False
    if violations:
        out["_permiso_violado"] = violations
    return out, violations


def record_violation(store: Any, project_id: str, *, actor: str, kind: str,
                     violations: list[str], parent_id: str | None = None) -> None:
    """El INTENTO de violación es información de seguridad epistémica: degradar
    silenciosamente escondería que una ruta intenta elevar resultados sin
    autorización. Si mañana algo lo intenta 300 veces, estas filas lo delatan.
    Best-effort: registrar el evento jamás rompe la escritura original."""
    import time
    try:
        store.put(project_id, "violation", f"viol_{int(time.time() * 1000)}",
                  {"actor_intento": actor, "kind_objetivo": kind,
                   "violaciones": violations, "origin": "permisos-mecanicos"},
                  status="FLAGGED", parent_id=parent_id, actor="Sistema",
                  summary=f"intento no autorizado: {actor}→{kind}: "
                          f"{violations[0][:90]}")
    except Exception:  # noqa: BLE001
        pass
