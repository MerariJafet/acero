"""Gödel — ACERO's mechanized prover, a level above Euclides (sympy).

Euclides (`formal_verify`, sympy) proves algebra/analysis but does NOT speak the language
of LOGIC and COUNTING — quantified statements over the integers, pigeonhole-style bounds,
propositional reasoning. Those are exactly the arguments that left conjecture B stuck at
"needs_human_review".

Gödel adds a real mechanized backend behind the same kind of interface. The pragmatic,
installable-today engine is **Z3** (an SMT solver): it decides many quantifier-free and
some quantified formulas over integers/reals/booleans — proving or refuting with a
concrete counterexample. A full **Lean** backend (interactive, mathlib) can plug in later
behind the same `prove()` facade; it is a heavy install and intentionally separate.

Honesty (same discipline as Euclides):
  * `proved`  — the negation is UNSAT: the statement holds for all values (within the
    declared theory). A real machine-checked result.
  * `refuted` — a concrete counterexample (a model) exists.
  * `unknown` — the solver couldn't decide (or Z3 isn't installed). Never upgraded.

The claim is given as a Python-operator expression over declared variables (Z3 overloads
`+ - * <= >= == And/Or/Not/Implies`), evaluated in a restricted namespace (no builtins) —
the same trust model as sympy's `sympify` in Euclides.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

RESULTS = ("proved", "refuted", "unknown")
KINDS = ("int_forall", "real_forall", "bool_forall", "int_exists", "bool_sat")


def available() -> bool:
    try:
        import z3  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _out(result: str, kind: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"result": result, "kind": kind, "detail": detail, "backend": "z3", **extra}


def _env(names: list[str], sort: str) -> dict[str, Any]:
    import z3
    mk = {"int": z3.Int, "real": z3.Real, "bool": z3.Bool}.get(sort, z3.Int)
    env: dict[str, Any] = {n: mk(n) for n in names}
    for fn in ("And", "Or", "Not", "Implies", "If", "Xor", "Distinct", "Sum"):
        if hasattr(z3, fn):
            env[fn] = getattr(z3, fn)
    return env


def _model(m: Any) -> dict[str, str]:
    try:
        return {str(d.name()): str(m[d]) for d in m.decls()}
    except Exception:  # noqa: BLE001
        return {}


def _default_timeout_s() -> float:
    """Techo de pared del solve. Generoso a propósito: DÍAS, no minutos — Gödel debe
    poder pensar en serio (Merari: "no pongas límite de tiempo al programa"). Lo que
    NO puede es hacerlo invisible y dentro del proceso del ciclo."""
    import os
    try:
        return float(os.environ.get("ACERO_Z3_TIMEOUT_S") or 3 * 86400.0)
    except ValueError:
        return 3 * 86400.0


def prove(kind: str, *, timeout_s: float | None = None,
          on_beat: Any = None, beat_every_s: float = 60.0,
          **kw: Any) -> dict[str, Any]:
    """Decide a claim with Z3 EN UN PROCESO HIJO, con latido.

    Por qué hijo y no aquí: `Solver.check()` es una llamada C++ bloqueante que no se
    puede interrumpir desde Python ni emite señal alguna. Corriéndola in-process, un
    solo solve secuestra el ciclo entero del Consejo sin dejar rastro — se observó en
    vivo un check() de 13.24 HORAS de CPU (2.4 GB) que dejó a la Ronda 4 congelada en
    la jugada 51, indistinguible de un cuelgue salvo hurgando en /proc.

    El portafolio de Caccetta–Häggkvist ya hacía lo correcto (z3 en procesos aparte con
    techo explícito de 7 y 10 días); esto le da a Gödel la misma disciplina.

    `on_beat(elapsed_s)` se llama cada `beat_every_s` mientras el hijo trabaja: el
    tablero puede mostrar que sigue vivo sin esperar al veredicto. Agotar el techo es
    un `unknown` HONESTO, nunca se promueve a proved/refuted."""
    timeout = _default_timeout_s() if timeout_s is None else float(timeout_s)
    if not available():
        return _out("unknown", kind, "Z3 no está instalado (backend Gödel no disponible)")
    import multiprocessing as mp
    import time as _time
    try:
        ctx = mp.get_context("fork")
        q: Any = ctx.Queue(1)
        p = ctx.Process(target=_prove_child, args=(q, kind, kw), daemon=True)
        t0 = _time.time()
        p.start()
        while True:
            p.join(max(1.0, min(beat_every_s, timeout)))
            if not p.is_alive():
                break
            elapsed = _time.time() - t0
            if elapsed >= timeout:
                p.kill()
                p.join(5)
                return _out("unknown", kind,
                            f"timeout: el solve excedió {timeout / 3600:.1f} h "
                            "(sin veredicto — NO se promueve a proved/refuted)")
            if on_beat:
                try:
                    on_beat(elapsed)
                except Exception:  # noqa: BLE001 - el latido jamás rompe el solve
                    pass
        return q.get(timeout=5)
    except Exception:  # noqa: BLE001 - sin proceso hijo, mejor resolver que no resolver
        log.error(
            "prove(): fallo al lanzar/vigilar el proceso hijo aislado (fork) para "
            "kind=%r — cayendo a _prove_direct SIN aislamiento de proceso ni techo de "
            "tiempo. Esto reproduce el patrón de la Ronda 4 (ver docstring de prove()): "
            "un solve que se cuelga aquí será indistinguible de un cuelgue del proceso "
            "llamador salvo hurgando en /proc.",
            kind, exc_info=True,
        )
        result = _prove_direct(kind, **kw)
        result["degraded_no_isolation"] = True
        return result


def _prove_child(q: Any, kind: str, kw: dict[str, Any]) -> None:
    q.put(_prove_direct(kind, **kw))


def _prove_direct(kind: str, **kw: Any) -> dict[str, Any]:
    """El solve real, sin techo (corre dentro del hijo). `expr` is the statement;
    `vars` the free symbols; `assume` an optional list of hypotheses; `sort` in
    {int, real, bool}. Never raises."""
    if not available():
        return _out("unknown", kind, "Z3 no está instalado (backend Gödel no disponible)")
    import z3
    names = kw.get("vars") or ["n"]
    sort = str(kw.get("sort") or ("bool" if kind.startswith("bool") else "int"))
    env = _env(list(names), sort)
    safe: dict[str, Any] = {"__builtins__": {}}
    try:
        target = eval(str(kw["expr"]), safe, env)  # noqa: S307 - restricted namespace
    except KeyError:
        return _out("unknown", kind, "falta 'expr'")
    except Exception as exc:  # noqa: BLE001
        return _out("unknown", kind, f"expresión no evaluable: {str(exc)[:140]}")
    s = z3.Solver()
    for c in (kw.get("assume") or []):
        try:
            s.add(eval(str(c), safe, env))  # noqa: S307
        except Exception:  # noqa: BLE001
            continue
    try:
        if kind in ("int_forall", "real_forall", "bool_forall"):
            # prove ∀: the negation must be unsatisfiable (under the hypotheses)
            s.add(z3.Not(target))
            r = s.check()
            if r == z3.unsat:
                return _out("proved", kind, "∀ se cumple (negación UNSAT en Z3)")
            if r == z3.sat:
                return _out("refuted", kind, "existe un contraejemplo",
                            counterexample=_model(s.model()))
            return _out("unknown", kind, "Z3 no decidió (unknown)")
        if kind in ("int_exists", "bool_sat"):
            s.add(target)
            r = s.check()
            if r == z3.sat:
                return _out("proved", kind, "existe testigo (SAT)",
                            witness=_model(s.model()))
            if r == z3.unsat:
                return _out("refuted", kind, "no existe (UNSAT)")
            return _out("unknown", kind, "Z3 no decidió (unknown)")
        return _out("unknown", kind, f"tipo no soportado: {kind!r}")
    except Exception as exc:  # noqa: BLE001
        return _out("unknown", kind, f"Z3 falló: {str(exc)[:140]}")
