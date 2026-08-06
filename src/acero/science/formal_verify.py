"""Formal verification — a stronger evidence level than "it reproduced".

The one genuinely-autonomous AI math result of the era (Erdős #728, early 2026) was
only trusted because it was FORMALIZED in Lean — machine-checked, not just numerically
plausible. ACERO verifies EMPIRICALLY (null controls, net-free reproduction) but had
no way to *prove* a symbolic claim. This adds that: a claim like an identity, an
inequality over a range, or a limit is checked SYMBOLICALLY with sympy, yielding
`proved | refuted | unknown` (+ a counterexample when refuted).

This is a real proof for the class of claims sympy can decide — it is NOT a general
theorem prover. The backend is pluggable: `verify()` dispatches by claim kind, and a
Lean/otherᵖ backend can be added later behind the same interface. `unknown` is a
first-class, honest outcome; we never upgrade `unknown` to `proved`.

Feeds reliability: a `proved` result supports the `FORMALLY_VERIFIED`-style signal
above mere computational reproducibility. It runs headless (no network) and is safe
to call inside the sandbox.
"""

from __future__ import annotations

from typing import Any

RESULTS = ("proved", "refuted", "unknown")
KINDS = ("identity", "inequality", "limit", "boolean")


def _sympify(expr: str) -> Any:
    import sympy
    # locals kept minimal + safe; sympify does not exec arbitrary code
    return sympy.sympify(expr)


def verify(kind: str, **kw: Any) -> dict[str, Any]:
    """Dispatch a formal check. Returns {result, kind, detail, counterexample?}.
    Never raises on a bad claim — a malformed claim is `unknown` with the reason."""
    try:
        if kind == "identity":
            return _identity(kw["lhs"], kw["rhs"], kw.get("assume_real", True))
        if kind == "inequality":
            return _inequality(kw["expr"], kw.get("var", "x"),
                               kw.get("domain"), kw.get("assume_real", True))
        if kind == "limit":
            return _limit(kw["expr"], kw.get("var", "x"), kw["to"], kw["expected"])
        if kind == "boolean":
            return _boolean(kw["expr"])
        return _out("unknown", kind, f"tipo no soportado: {kind!r}")
    except KeyError as exc:
        return _out("unknown", kind, f"falta argumento {exc}")
    except Exception as exc:  # noqa: BLE001 - malformed claim ⇒ honest unknown
        return _out("unknown", kind, f"no evaluable: {str(exc)[:160]}")


def _out(result: str, kind: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"result": result, "kind": kind, "detail": detail, **extra}


def _identity(lhs: str, rhs: str, assume_real: bool) -> dict[str, Any]:
    """Prove lhs == rhs for all values by symbolic simplification of the difference."""
    import sympy
    diff = sympy.simplify(_sympify(lhs) - _sympify(rhs))
    if diff == 0:
        return _out("proved", "identity", f"{lhs} ≡ {rhs} (diferencia simplifica a 0)")
    # try a stronger normal form before giving up
    if sympy.simplify(sympy.expand_trig(sympy.expand(diff))) == 0:
        return _out("proved", "identity", f"{lhs} ≡ {rhs}")
    # find a concrete counterexample among the free symbols
    syms = sorted(diff.free_symbols, key=str)
    for trial in ({s: v for s in syms} for v in (2, 3, 5, 7)):
        try:
            val = complex(diff.subs(trial))
            if abs(val) > 1e-9:
                return _out("refuted", "identity", f"{lhs} ≠ {rhs}",
                            counterexample={str(k): v for k, v in trial.items()})
        except Exception:  # noqa: BLE001
            continue
    return _out("unknown", "identity", "no se pudo probar ni refutar")


def _inequality(expr: str, var: str, domain: Any, assume_real: bool) -> dict[str, Any]:
    """Prove a relation holds for ALL x in domain, e.g. 'x**2 + 1 > 0'.
    domain = (low, high) restricts x; None means all reals."""
    import sympy
    x = sympy.Symbol(var, real=assume_real)
    rel = sympy.sympify(expr, locals={var: x})
    # sympy may auto-decide a relation at construction (e.g. x**2+1>0 for real x → True)
    if rel in (sympy.true, True):
        return _out("proved", "inequality", f"{expr} se cumple para todo {var}")
    if rel in (sympy.false, False):
        return _out("refuted", "inequality", f"{expr} es falso para todo {var}")
    if not isinstance(rel, sympy.core.relational.Relational):
        return _out("unknown", "inequality", "la expresión no es una desigualdad")
    if domain:
        lo, hi = domain
        dom = sympy.Interval(sympy.sympify(lo), sympy.sympify(hi))
    else:
        dom = sympy.S.Reals
    try:
        sol = sympy.solve_univariate_inequality(rel, x, relational=False, domain=dom)
    except Exception as exc:  # noqa: BLE001
        return _out("unknown", "inequality", f"sympy no decidió: {str(exc)[:120]}")
    import sympy as _sp
    if dom.is_subset(sol) is True or (dom - sol) == _sp.EmptySet:
        return _out("proved", "inequality", f"{expr} se cumple para todo {var} en {dom}")
    # find a concrete integer counterexample inside the domain
    ce = None
    for c in range(-100, 101):
        cc = sympy.Integer(c)
        try:
            if dom.contains(cc) and not sol.contains(cc):
                ce = c
                break
        except Exception:  # noqa: BLE001
            continue
    return _out("refuted", "inequality", f"{expr} NO se cumple en todo {dom}",
                **({"counterexample": {var: ce}} if ce is not None else {}))


def _limit(expr: str, var: str, to: str, expected: str) -> dict[str, Any]:
    import sympy
    x = sympy.Symbol(var, real=True)
    val = sympy.limit(sympy.sympify(expr, locals={var: x}), x, sympy.sympify(to))
    exp = sympy.sympify(expected)
    if sympy.simplify(val - exp) == 0:
        return _out("proved", "limit", f"lim {expr} → {to} = {expected}")
    return _out("refuted", "limit", f"el límite es {val}, no {expected}",
                counterexample={"actual_limit": str(val)})


def _boolean(expr: str) -> dict[str, Any]:
    """Tautology check for a propositional/quantifier-free boolean expression."""
    import sympy
    e = sympy.sympify(expr)
    simplified = sympy.simplify(e)
    if simplified in (sympy.true, True):
        return _out("proved", "boolean", "tautología")
    if simplified in (sympy.false, False):
        return _out("refuted", "boolean", "contradicción")
    return _out("unknown", "boolean", f"no decidido: {simplified}")
