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

    def _codegen(self, claim: str, feedback: str) -> str:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            raise RuntimeError("sin proveedor para codegen")
        fb = "\n\nEL INTENTO ANTERIOR NO CONCLUYÓ. Prueba OTRO método (más N, casos "
        fb += f"borde, otra reformulación, búsqueda más lista):\n{feedback[:800]}" if feedback else ""
        prompt = f"{_CODEGEN_SYS}\n\nAFIRMACIÓN: {claim}{fb}"
        code = prov.complete(prompt, temperature=0.2, max_tokens=2500).text.strip()
        code = re.sub(r"^```(?:python)?\s*", "", code)
        return re.sub(r"\s*```$", "", code)

    def probe(self, claim: str, *, formal_claim: dict[str, Any] | None = None,
              max_tries: int = 3) -> dict[str, Any]:
        """Attack the claim. Returns the overall verdict + computational & formal evidence."""
        formal = self._formal_check(formal_claim)
        # a formal proof or refutation is decisive — no need to search further
        if formal and formal.get("result") == "refuted":
            return self._pack("refuted", None, formal, [], "refutado formalmente")
        computational: dict[str, Any] | None = None
        attempts: list[dict[str, Any]] = []
        feedback = ""
        for i in range(max_tries):
            try:
                code = self._codegen(claim, feedback)
            except Exception as exc:  # noqa: BLE001
                attempts.append({"try": i + 1, "error": f"codegen: {str(exc)[:150]}"})
                break
            stdout, stderr, rc = self._run(code)
            parsed = _extract(stdout)
            attempts.append({"try": i + 1, "rc": rc,
                             "verdict": (parsed or {}).get("verdict"),
                             "n_tested": (parsed or {}).get("n_tested"),
                             "error": (stderr or "")[-200:] if rc != 0 else ""})
            if parsed and parsed.get("verdict") == "refuted":
                computational = parsed
                break
            if parsed and parsed.get("verdict") == "holds_empirically":
                computational = parsed  # keep, but keep trying to strengthen/refute
                feedback = (f"Antes no se halló contraejemplo tras {parsed.get('n_tested')} "
                            "casos; intenta un espacio distinto o casos borde por si acaso.")
                continue
            feedback = (f"status rc={rc}; salida no concluyó. "
                        f"{(stderr or '')[-300:] or (stdout or '')[-200:]}")
        return self._decide(claim, computational, formal, attempts)

    @staticmethod
    def _pack(verdict: str, computational: Any, formal: Any,
              attempts: list[dict[str, Any]], detail: str) -> dict[str, Any]:
        return {"verdict": verdict, "computational": computational, "formal": formal,
                "attempts": attempts, "detail": detail}

    def _decide(self, claim: str, computational: dict[str, Any] | None,
                formal: dict[str, Any] | None,
                attempts: list[dict[str, Any]]) -> dict[str, Any]:
        # formal proof is the only path to 'verified' (a real demonstration)
        if formal and formal.get("result") == "proved":
            return self._pack("verified", computational, formal, attempts,
                              "demostrado formalmente (sympy)")
        comp = computational or {}
        cv = comp.get("verdict")
        if cv == "refuted":
            return self._pack("refuted", computational, formal, attempts,
                              f"contraejemplo: {comp.get('counterexample')}")
        if cv == "holds_empirically":
            return self._pack("holds_empirically", computational, formal, attempts,
                              f"sin contraejemplo en {comp.get('n_tested')} casos "
                              "(NO es prueba)")
        return self._pack("inconclusive", computational, formal, attempts,
                          "ni confirmado ni refutado — ACERO se abstiene")
