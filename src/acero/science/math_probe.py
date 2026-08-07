"""Experimental math prover — ACERO attacks a mathematical claim the way it does
science, not by writing a Lean proof: it COMPUTES.

For a claim like "for all n, f(n) <= g(n)" it:
  1. CODEGEN: an LLM writes a self-contained Python program that hunts for a
     counterexample over a huge search space and/or verifies the claim on all
     tested cases, printing one RESULT_JSON line.
  2. RUN it in the network-free sandbox (deterministic, resource-capped).
  3. FORMAL cross-check: if the claim reduces to a symbolic identity/inequality/
     limit, `formal_verify` tries to PROVE or REFUTE it exactly (sympy).
  4. SELF-CRITIQUE + CREATIVE RETRY: if inconclusive, feed the weakness back and
     let the agent try a DIFFERENT method (bigger N, edge cases, reformulation,
     a smarter search) — up to `max_tries` times.

Overall verdict, honest by construction:
  * refuted            — a concrete counterexample exists (computational or formal).
  * verified           — formally PROVED (strongest; a real demonstration).
  * holds_empirically  — no counterexample across a large search, but NOT proved.
  * inconclusive       — neither confirmed nor refuted; ACERO abstains.

`holds_empirically` is NEVER upgraded to `verified` — searching a lot is not a
proof. Provider, sandbox runner and the formal backend are injectable for tests.
"""

from __future__ import annotations

import json
import re
from typing import Any

_RESULT_RE = re.compile(r"RESULT_JSON:\s*(\{.*\})", re.DOTALL)

_CODEGEN_SYS = (
    "Eres un MATEMÁTICO COMPUTACIONAL en ACERO. Te doy una AFIRMACIÓN. Escribe UN "
    "programa Python autocontenido (solo stdlib + numpy/sympy) que la ATAQUE "
    "computacionalmente: busca un CONTRAEJEMPLO en el espacio más grande que sea "
    "razonable (~segundos) y/o verifica que se cumple en TODOS los casos probados. "
    "PROHIBIDO: red, subprocess, os.system, leer archivos. Determinista "
    "(numpy.random.default_rng(0)). Al final imprime EXACTAMENTE una línea:\n"
    "RESULT_JSON: {\"verdict\": \"refuted|holds_empirically|inconclusive\", "
    "\"counterexample\": <valor o null>, \"n_tested\": <int>, \"detail\": <str>}\n"
    "verdict='refuted' SOLO si encontraste un contraejemplo concreto (ponlo en "
    "counterexample). 'holds_empirically' si NO hallaste contraejemplo tras probar "
    "muchos casos. 'inconclusive' si no pudiste probar suficiente. NUNCA afirmes "
    "'demostrado': buscar no es probar. Responde SOLO con el código."
)


def _extract(stdout: str) -> dict[str, Any] | None:
    m = list(_RESULT_RE.finditer(stdout or ""))
    if not m:
        return None
    try:
        return json.loads(m[-1].group(1))
    except Exception:  # noqa: BLE001
        return None


def _robust_counterexample(ce: Any) -> bool:
    """A trustworthy counterexample to an EXACT claim is a gross mismatch, not
    floating-point noise. If a numeric 'counterexample' is within ~0.1% of the
    expected value, it is a precision artifact (the script's tolerance was tighter
    than its own accuracy), NOT a refutation."""
    if not isinstance(ce, dict):
        return True   # a concrete integer/structure counterexample — trust it

    def _f(x: Any) -> float | None:
        try:
            return abs(float(x))
        except Exception:  # noqa: BLE001
            return None
    exp = _f(ce.get("expected"))
    comp = _f(ce.get("computed"))
    ae = _f(ce.get("abs_error"))
    if exp is not None and (comp is not None or ae is not None):
        err = ae if ae is not None else abs((comp or 0.0) - exp)
        denom = exp or 1.0
        return (err / denom) > 1e-3    # >0.1% off ⇒ real; else numeric near-miss
    # convergence/truncation artifact: a 'counterexample' justified by a tiny leftover
    # tail/residual is not a refutation — the series just wasn't summed far enough.
    for k, v in ce.items():
        if any(t in str(k).lower() for t in ("tail", "residual", "truncation")):
            fv = _f(v)
            if fv is not None and fv < 1e-3:
                return False
    return True


class MathProbe:
    def __init__(self, *, provider: Any = None, runner: Any = None,
                 formal: Any = None) -> None:
        self._provider = provider
        self._runner = runner
        self._formal = formal

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider(timeout_sec=220)

    def _run(self, code: str) -> tuple[str, str, int]:
        if self._runner is not None:
            return self._runner(code)
        import tempfile

        from ..sandbox.runner import SubprocessRunner
        with tempfile.TemporaryDirectory() as tmp:
            res = SubprocessRunner().run(code, tmp, timeout_sec=60, memory_mb=2048,
                                         cpu_seconds=60, allow_network=False)
            return res.stdout, res.stderr, res.exit_code

    def _formal_check(self, formal_claim: dict[str, Any] | None) -> dict[str, Any] | None:
        if not formal_claim:
            return None
        if self._formal is not None:
            return self._formal(formal_claim)
        from .formal_verify import verify
        kind = str(formal_claim.get("kind") or "")
        kw = {k: v for k, v in formal_claim.items() if k != "kind"}
        return verify(kind, **kw)

    def _codegen(self, claim: str, feedback: str, prev_code: str = "",
                 crashed: bool = False) -> str:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            raise RuntimeError("sin proveedor para codegen")
        fb = ""
        if crashed and prev_code:
            # the previous script errored: FIX it, don't start over blindly.
            fb = ("\n\nEL CÓDIGO ANTERIOR FALLÓ AL EJECUTAR. Aquí está; CORRÍGELO "
                  "(mismo enfoque, arregla el error) y devuelve el archivo completo:\n"
                  f"```python\n{prev_code[:2500]}\n```\nERROR:\n{feedback[:600]}")
        elif feedback:
            fb = ("\n\nEL INTENTO ANTERIOR NO CONCLUYÓ. Prueba OTRO método (más N, "
                  f"casos borde, otra reformulación, búsqueda más lista):\n{feedback[:800]}")
        prompt = f"{_CODEGEN_SYS}\n\nAFIRMACIÓN: {claim}{fb}"
        code = prov.complete(prompt, temperature=0.2, max_tokens=2500).text.strip()
        code = re.sub(r"^```(?:python)?\s*", "", code)
        return re.sub(r"\s*```$", "", code)

    def probe(self, claim: str, *, formal_claim: dict[str, Any] | None = None,
              max_tries: int = 3) -> dict[str, Any]:
        """Attack the claim. Returns the overall verdict + computational & formal evidence."""
        formal = self._formal_check(formal_claim)
        # NOTE: we do NOT short-circuit on a formal 'refuted'. A formal_claim can be
        # MISENCODED (e.g. a wrong sympy translation of a true theorem), so a lone
        # formal refutation is reconciled against the computational search in _decide.
        computational: dict[str, Any] | None = None
        attempts: list[dict[str, Any]] = []
        feedback = ""
        prev_code = ""
        crashed = False
        last_good_code = ""     # the last script that RAN (retry can build on it)
        for i in range(max_tries):
            try:
                code = self._codegen(claim, feedback, prev_code, crashed)
            except Exception as exc:  # noqa: BLE001
                attempts.append({"try": i + 1, "error": f"codegen: {str(exc)[:150]}"})
                break
            stdout, stderr, rc = self._run(code)
            prev_code = code
            parsed = _extract(stdout)
            crashed = (rc != 0) or (parsed is None)
            attempts.append({"try": i + 1, "rc": rc,
                             "verdict": (parsed or {}).get("verdict"),
                             "n_tested": (parsed or {}).get("n_tested"),
                             "error": (stderr or "")[-200:] if rc != 0 else ""})
            if parsed and parsed.get("verdict") == "refuted":
                computational = parsed
                break
            if parsed and parsed.get("verdict") == "holds_empirically":
                computational = parsed  # a working script; try to strengthen/refute from it
                last_good_code = code
                prev_code = last_good_code
                feedback = (f"Este código corrió bien (sin contraejemplo en "
                            f"{parsed.get('n_tested')} casos). Amplíalo: prueba un espacio "
                            "distinto o casos borde por si hay un contraejemplo.")
                continue
            # crashed / inconclusive → next round fixes the code we have
            feedback = (stderr or "")[-500:] or (stdout or "")[-300:] or "no imprimió RESULT_JSON"
        return self._decide(claim, computational, formal, attempts)

    @staticmethod
    def _pack(verdict: str, computational: Any, formal: Any,
              attempts: list[dict[str, Any]], detail: str) -> dict[str, Any]:
        return {"verdict": verdict, "computational": computational, "formal": formal,
                "attempts": attempts, "detail": detail}

    def _decide(self, claim: str, computational: dict[str, Any] | None,
                formal: dict[str, Any] | None,
                attempts: list[dict[str, Any]]) -> dict[str, Any]:
        # formal PROOF is the only path to 'verified' (a real demonstration)
        if formal and formal.get("result") == "proved":
            return self._pack("verified", computational, formal, attempts,
                              "demostrado formalmente (sympy)")
        comp = computational or {}
        cv = comp.get("verdict")
        # --- computational refutation: only trust a ROBUST counterexample ---------
        if cv == "refuted":
            ce = comp.get("counterexample")
            if _robust_counterexample(ce):
                return self._pack("refuted", computational, formal, attempts,
                                  f"contraejemplo: {ce}")
            # a numeric near-miss is NOT a refutation — the value actually holds
            return self._pack("holds_empirically", computational, formal, attempts,
                              "el 'contraejemplo' es ruido numérico (near-miss); "
                              "la igualdad se sostiene — NO es prueba")
        # --- formal refutation: reconcile against the search ----------------------
        if formal and formal.get("result") == "refuted":
            if cv == "holds_empirically":
                # CONFLICT: formal says false but no counterexample exists → the
                # formal_claim is probably misencoded. Abstain honestly, don't refute.
                return self._pack("inconclusive", computational, formal, attempts,
                                  "conflicto: la verificación formal refuta pero la "
                                  "búsqueda no halla contraejemplo — probable error de "
                                  "codificación formal; ACERO se abstiene")
            return self._pack("refuted", computational, formal, attempts,
                              "refutado formalmente (sin evidencia empírica en contra)")
        if cv == "holds_empirically":
            return self._pack("holds_empirically", computational, formal, attempts,
                              f"sin contraejemplo en {comp.get('n_tested')} casos "
                              "(NO es prueba)")
        return self._pack("inconclusive", computational, formal, attempts,
                          "ni confirmado ni refutado — ACERO se abstiene")
