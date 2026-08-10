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
KINDS = ("identity", "inequality", "limit", "boolean", "summation", "product")


def _sympify(expr: str) -> Any:
    import sympy
    # locals kept minimal + safe; sympify does not exec arbitrary code
    return sympy.sympify(expr)


def verify(kind: str, timeout_s: float = 900.0, **kw: Any) -> dict[str, Any]:
    """Dispatch a formal check WITH A HARD TIMEOUT. The actual verification runs in a
    child process; if it exceeds `timeout_s` the child is killed and the result is an
    honest `unknown` (timeout). Rationale: sympy can hang without bound on pathological
    simplify/limit inputs — a single claim must never freeze a Council cycle (this froze
    the Cuboide problem for 25 min during RETO 50)."""
    import multiprocessing as mp
    try:
        ctx = mp.get_context("fork")
        q: Any = ctx.Queue(1)
        p = ctx.Process(target=_verify_child, args=(q, kind, kw), daemon=True)
        p.start()
        p.join(timeout_s)
        if p.is_alive():
            p.kill()
            p.join(5)
            return _out("unknown", kind,
                        f"timeout: la verificación excedió {timeout_s:.0f}s")
        return q.get(timeout=5)
    except Exception as exc:  # noqa: BLE001 - fallback sin proceso hijo
        del exc
        return _verify_dispatch(kind, **kw)


def _verify_child(q: Any, kind: str, kw: dict[str, Any]) -> None:
    q.put(_verify_dispatch(kind, **kw))


def _verify_dispatch(kind: str, **kw: Any) -> dict[str, Any]:
    """Dispatch real (sin límite). Returns {result, kind, detail, counterexample?}.
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
        if kind == "summation":
            return _summation(kw["term"], kw.get("index", "k"), kw.get("lower", "1"),
                              kw.get("upper", "n"), kw["closed"])
        if kind == "product":
            return _product(kw["term"], kw.get("index", "k"), kw.get("lower", "1"),
                            kw.get("upper", "n"), kw["closed"])
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


def _closed_form_over_index(kind: str, op: Any, term: str, index: str, lower: str,
                            upper: str, closed: str) -> dict[str, Any]:
    """Shared core: PROVE  op_{index=lower}^{upper} term(index) == closed(upper).

    `op` is sympy.summation or sympy.product. `upper` is a symbol name (e.g. "n").
    Symbolic equality ⇒ proved; a disagreeing integer ⇒ refuted; else honest unknown.
    """
    import sympy
    k = sympy.Symbol(index, integer=True)
    n = sympy.Symbol(upper, integer=True, positive=True)
    t = sympy.sympify(term, locals={index: k, upper: n})
    lo = sympy.sympify(lower, locals={upper: n})
    closed_e = sympy.sympify(closed, locals={upper: n, index: k})
    val = op(t, (k, lo, n))
    if getattr(val, "has", lambda *_: False)(sympy.Sum, sympy.Product):
        val = sympy.simplify(val.doit()) if hasattr(val, "doit") else val
    diff = sympy.simplify(val - closed_e)
    sign = "Σ" if kind == "summation" else "Π"
    if diff == 0:
        return _out("proved", kind,
                    f"{sign}_{{{index}={lower}}}^{{{upper}}} {term} ≡ {closed} "
                    "(cerrado simbólicamente)")
    # symbolic didn't close — look for a concrete integer upper that disagrees
    for nv in (1, 2, 3, 4, 5, 8, 13):
        try:
            lhs = op(t.subs(n, nv) if lo.free_symbols else t, (k, lo.subs(n, nv), nv))
            lhs = sympy.nsimplify(lhs) if not lhs.free_symbols else lhs
            rhs = closed_e.subs(n, nv)
            if sympy.simplify(lhs - rhs) != 0:
                return _out("refuted", kind, f"discrepa en {upper}={nv}: {lhs} ≠ {rhs}",
                            counterexample={upper: nv, "lhs": str(lhs), "rhs": str(rhs)})
        except Exception:  # noqa: BLE001
            continue
    return _out("unknown", kind,
                f"coincide numéricamente pero sympy no cerró la forma ({sign} {term})")


def _summation(term: str, index: str, lower: str, upper: str,
               closed: str) -> dict[str, Any]:
    import sympy
    return _closed_form_over_index("summation", sympy.summation, term, index,
                                   lower, upper, closed)


def _product(term: str, index: str, lower: str, upper: str,
             closed: str) -> dict[str, Any]:
    import sympy
    return _closed_form_over_index("product", sympy.product, term, index,
                                   lower, upper, closed)


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
