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

from typing import Any

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


def prove(kind: str, **kw: Any) -> dict[str, Any]:
    """Decide a claim with Z3. `expr` is the statement; `vars` the free symbols; `assume`
    an optional list of hypotheses; `sort` in {int, real, bool}. Never raises."""
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
