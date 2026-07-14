"""Symbolic search & Codex-proposed terms (Sprint 8.8).

Codex may PROPOSE candidate terms/expressions via a strict JSON schema. ACERO does
NOT accept them: each is validated (parseable by SymPy, finite on the data, within
domain) before it can enter a library. Codex is never evidence.
"""

from __future__ import annotations

from typing import Any

import numpy as np

TERM_SCHEMA = {
    "type": "object",
    "properties": {
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"expression": {"type": "string"},
                               "rationale": {"type": "string"}},
                "required": ["expression", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["terms"],
    "additionalProperties": False,
}

_PROMPT = """Propose candidate mathematical TERMS that might appear in the governing equation
d{target}/dt = f(...) for the phenomenon below. Give short symbolic expressions in the
variables {variables} (e.g. 'x', 'x**2', 'x*y', 'sin(x)'), each with a one-line
rationale. Do NOT claim any term is correct — they will be tested. Return JSON only.

Phenomenon: {phenomenon}
Observed variables: {variables}"""


def propose_terms(provider: Any, phenomenon: str, variables: list[str], target: str = "x"
                  ) -> dict[str, Any]:
    if not hasattr(provider, "complete_json"):
        raise TypeError("term proposal requires a provider with complete_json")
    prompt = _PROMPT.format(phenomenon=phenomenon, variables=variables, target=target)
    result = provider.complete_json(prompt, TERM_SCHEMA)
    result["_provenance"] = {
        "provider": getattr(provider, "name", "unknown"),
        "model": getattr(provider, "model", None) or "codex-default",
        "token_usage": getattr(provider, "last_usage", {}) or {},
    }
    return result


def validate_terms(proposed: list[dict[str, Any]], data: dict[str, np.ndarray]
                   ) -> list[dict[str, Any]]:
    """Keep only terms that parse and evaluate to finite values on the data."""
    import sympy as sp

    syms = {v: sp.Symbol(v) for v in data}
    out = []
    for item in proposed:
        expr_str = item.get("expression", "")
        try:
            expr = sp.sympify(expr_str, locals=syms)
            free = {str(s) for s in expr.free_symbols}
            if not free.issubset(set(data)):
                out.append({"expression": expr_str, "valid": False,
                            "reason": f"unknown symbols {free - set(data)}"})
                continue
            fn = sp.lambdify([syms[v] for v in data], expr, "numpy")
            vals = np.asarray(fn(*[data[v] for v in data]), dtype=float)
            finite = bool(np.all(np.isfinite(vals)))
            out.append({"expression": expr_str, "valid": finite,
                        "reason": "ok" if finite else "non-finite on data"})
        except Exception as exc:  # noqa: BLE001 - a bad term is invalid, not a crash
            out.append({"expression": expr_str, "valid": False, "reason": f"unparseable: {exc}"})
    return out
