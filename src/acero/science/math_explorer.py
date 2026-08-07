"""Math Explorer — the exploratory, goal-directed mind ACERO was missing.

The math prover is REACTIVE: give it a claim, it tests it. This is PROACTIVE: give
it a GOAL ("find the area of a rectangle", "find a relation for X") and it thinks in
MULTIPLE approaches — measure/sample, search a formula, use calculus, algebra,
geometry, dimensional analysis — assembles each as a runnable script from a powerful
math library (numpy/sympy/scipy, the "LEGO pieces"), RUNS them, keeps the ones that
WORK, understands WHY, distills a precise HYPOTHESIS, and CONFRONTS it with the math
prover (counterexample search + formal proof) and the novelty check.

The loop (composes everything already built):

    GOAL
     ├─ diverge:   propose K distinct approaches (methods)
     ├─ assemble:  write + run a script per approach (sandbox, no network)
     ├─ select:    keep the viable ones; note what each found and why
     ├─ synthesize: a precise hypothesis + (if reducible) a formal claim
     ├─ confront:  MathProbe → refuted | verified | holds_empirically  (+ novelty)
     └─ loop:      if not settled, re-diverge with what was learned

Honesty is inherited: `holds_empirically` is never a proof; only a formal proof or a
confirmed counterexample is decisive; a discovered hypothesis is novelty-checked so we
never dress up a known result as new (anti-Erdősgate). Every LLM/runner/prober is
injectable for offline tests.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

_RESULT_RE = re.compile(r"RESULT_JSON:\s*(\{.*\})", re.DOTALL)

APPROACHES_SCHEMA = {
    "type": "object",
    "properties": {
        "approaches": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "method": {"type": "string"},        # short tag: numerico|algebra|calculo|...
                "plan": {"type": "string"},           # how this approach reaches the goal
                "tools_used": {"type": "array", "items": {"type": "string"}},  # catalog ids
                "why_might_work": {"type": "string"}},
            "required": ["method", "plan", "tools_used", "why_might_work"],
            "additionalProperties": False}},
    },
    "required": ["approaches"], "additionalProperties": False,
}

SYNTH_SCHEMA = {
    "type": "object",
    "properties": {
        "claim": {"type": "string"},                 # the precise hypothesis found
        "why": {"type": "string"},                    # why the viable approaches support it
        "formal_claim": {                             # optional reduction for sympy
            "type": "object",
            "properties": {
                "kind": {"type": "string"}, "lhs": {"type": "string"},
                "rhs": {"type": "string"}, "expr": {"type": "string"},
                "var": {"type": "string"}, "to": {"type": "string"},
                "expected": {"type": "string"},
                # summation/product fields
                "term": {"type": "string"}, "index": {"type": "string"},
                "lower": {"type": "string"}, "upper": {"type": "string"},
                "closed": {"type": "string"}},
            # Codex requires EVERY property key in `required`; unused ones come back
            # as "" and are stripped before reaching sympy.
            "required": ["kind", "lhs", "rhs", "expr", "var", "to", "expected",
                         "term", "index", "lower", "upper", "closed"],
            "additionalProperties": False},
    },
    "required": ["claim", "why", "formal_claim"], "additionalProperties": False,
}

_DIVERGE_SYS = (
    "Eres un MATEMÁTICO CREATIVO en ACERO. Te doy un OBJETIVO y una CAJA DE "
    "HERRAMIENTAS (piezas de LEGO que el programa ACERO pone a tu disposición, cada una "
    "con su id, para qué sirve y su idiom de código). Propón enfoques DISTINTOS entre sí "
    "que ENSAMBLEN esas piezas (puedes combinarlas y también usar otras si hiciera falta, "
    "pero PREFIERE las de la caja). Para cada enfoque: method (etiqueta corta), plan (cómo "
    "llegar al objetivo), tools_used (lista de ids de las piezas que usarás), "
    "why_might_work. Sé diverso; no repitas el mismo método."
)

_ASSEMBLE_SYS = (
    "Eres un MATEMÁTICO COMPUTACIONAL en ACERO. Implementa ESTE enfoque para el objetivo "
    "en UN programa Python autocontenido (solo stdlib + numpy/sympy/scipy/mpmath). Usa las "
    "PIEZAS indicadas (te doy sus idioms). El programa debe INTENTAR el objetivo con este "
    "enfoque y, si lo logra, reportar un RESULTADO concreto (una fórmula, una relación, un "
    "valor, una identidad). Cuando obtengas un valor numérico de una constante, intenta "
    "reconocer su forma cerrada (sympy.nsimplify). PROHIBIDO: red, subprocess, os.system, "
    "leer archivos. Determinista (semilla fija). Al final imprime EXACTAMENTE una línea:\n"
    "RESULT_JSON: {\"found\": <bool>, \"candidate\": <str: el resultado/fórmula o null>, "
    "\"checks\": <str: cómo lo comprobaste>, \"detail\": <str>}\n"
    "found=true SOLO si el enfoque produjo algo concreto y auto-consistente. Responde "
    "SOLO con el código."
)

_SYNTH_SYS = (
    "Eres el SINTETIZADOR de ACERO. Te doy un OBJETIVO y los RESULTADOS de los enfoques "
    "que SÍ funcionaron. Destila UNA hipótesis PRECISA y falsable (claim) que capture lo "
    "que convergió, explica POR QUÉ los enfoques la sostienen (why), y si se reduce a algo "
    "verificable simbólicamente, da formal_claim con el kind correcto:\n"
    " - identity: lhs, rhs (prueba lhs≡rhs)\n"
    " - inequality: expr, var\n"
    " - limit: expr, var, to, expected\n"
    " - boolean: expr\n"
    " - summation: term (f del índice), index (p.ej. k), lower, upper (p.ej. n), closed "
    "(forma cerrada en función de upper) — ¡ÚSALO para sumas tipo Σk = n(n+1)/2!\n"
    " - product: term, index, lower, upper, closed\n"
    "Rellena SOLO los campos del kind elegido; deja los demás en \"\". Si no se reduce, "
    "kind = \"\"."
)


def _extract(stdout: str) -> dict[str, Any] | None:
    m = list(_RESULT_RE.finditer(stdout or ""))
    if not m:
        return None
    try:
        return json.loads(m[-1].group(1))
    except Exception:  # noqa: BLE001
        return None


class MathExplorer:
    def __init__(self, *, provider: Any = None, runner: Any = None, probe: Any = None,
                 novelty: Any = None, catalog: Any = None, ledger: Any = None,
                 workers: int = 4) -> None:
        self._provider = provider
        self._runner = runner
        self._probe = probe
        self._novelty = novelty
        self._catalog = catalog
        self._ledger = ledger
        self._ledger_set = ledger is not None
        self._workers = max(1, workers)

    def _cat(self) -> Any:
        if self._catalog is not None:
            return self._catalog
        from .method_catalog import MethodCatalog
        self._catalog = MethodCatalog.default()
        return self._catalog

    def _led(self) -> Any:
        if self._ledger_set:
            return self._ledger
        import os

        from .explorer_ledger import ExplorerLedger
        base = Path(os.environ.get("ACERO_DATA_DIR", "acero_data")) / "explorer_ledger"
        self._ledger = ExplorerLedger(store=base)
        self._ledger_set = True
        return self._ledger

    # --- injectable primitives ------------------------------------------------
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
            r = SubprocessRunner().run(code, tmp, timeout_sec=60, memory_mb=2048,
                                       cpu_seconds=60, allow_network=False)
            return r.stdout, r.stderr, r.exit_code

    def _probe_claim(self, claim: str, formal_claim: dict[str, Any] | None) -> dict[str, Any]:
        if self._probe is not None:
            return self._probe(claim, formal_claim)
        from .math_probe import MathProbe
        return MathProbe(provider=self._provider, runner=self._runner).probe(
            claim, formal_claim=formal_claim, max_tries=2)

    def _check_novelty(self, claim: str) -> dict[str, Any] | None:
        if self._novelty is not None:
            return self._novelty(claim)
        try:
            from ..discovery.novelty_check import NoveltyChecker
            return NoveltyChecker(provider=self._provider).check(claim)
        except Exception:  # noqa: BLE001
            return None

    # --- steps ----------------------------------------------------------------
    def _diverge(self, goal: str, k: int, learned: str, hints: str = "") -> list[dict[str, Any]]:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return []
        toolbox = ""
        try:
            toolbox = self._cat().toolbox_text(goal, k=8)
        except Exception:  # noqa: BLE001
            toolbox = ""
        box = f"\n\nCAJA DE HERRAMIENTAS (piezas disponibles):\n{toolbox}" if toolbox else ""
        mem = f"\n\n{hints}" if hints else ""
        extra = f"\nYa aprendiste: {learned[:600]}. Propón enfoques NUEVOS." if learned else ""
        out = prov.complete_json(
            f"{_DIVERGE_SYS}\n\nOBJETIVO: {goal}{box}{mem}\nPropón {k} enfoques.{extra}",
            APPROACHES_SCHEMA, temperature=0.6)
        return (out.get("approaches") or [])[:k] if isinstance(out, dict) else []

    def _tool_idioms(self, ids: list[str]) -> str:
        try:
            cat = self._cat()
        except Exception:  # noqa: BLE001
            return ""
        lines = []
        for tid in ids or []:
            t = cat.get(tid) if hasattr(cat, "get") else None
            if t is not None:
                lines.append(t.brief())
        return "\n".join(lines)

    def _assemble_run(self, goal: str, approach: dict[str, Any]) -> dict[str, Any]:
        """Write + run one approach's script (the parallel unit)."""
        prov = self._prov()
        try:
            tools = approach.get("tools_used") or []
            idioms = self._tool_idioms(tools)
            piece = f"\nPIEZAS A USAR:\n{idioms}" if idioms else ""
            prompt = (f"{_ASSEMBLE_SYS}\n\nOBJETIVO: {goal}\n"
                      f"ENFOQUE ({approach.get('method')}): {approach.get('plan')}{piece}")
            code = prov.complete(prompt, temperature=0.2, max_tokens=2200).text.strip()
            code = re.sub(r"^```(?:python)?\s*", "", code)
            code = re.sub(r"\s*```$", "", code)
            stdout, stderr, rc = self._run(code)
            parsed = _extract(stdout) or {}
            return {"method": approach.get("method"), "plan": approach.get("plan"),
                    "tools_used": tools,
                    "found": bool(parsed.get("found")) and rc == 0,
                    "candidate": parsed.get("candidate"),
                    "checks": parsed.get("checks"), "rc": rc,
                    "error": (stderr or "")[-160:] if rc != 0 else ""}
        except Exception as exc:  # noqa: BLE001
            return {"method": approach.get("method"), "found": False,
                    "tools_used": approach.get("tools_used") or [],
                    "error": str(exc)[:160]}

    def _synthesize(self, goal: str, viable: list[dict[str, Any]]) -> dict[str, Any]:
        prov = self._prov()
        summary = "\n".join(f"- [{v['method']}] candidato: {v.get('candidate')} "
                            f"(comprobado: {v.get('checks')})" for v in viable)
        out = prov.complete_json(
            f"{_SYNTH_SYS}\n\nOBJETIVO: {goal}\nENFOQUES QUE FUNCIONARON:\n{summary}",
            SYNTH_SCHEMA, temperature=0.2)
        if not isinstance(out, dict):
            return {"claim": "", "why": "", "formal_claim": {}}
        fc = out.get("formal_claim") or {}
        # Codex fills every key; drop the empty placeholders so only the fields this
        # `kind` needs reach sympy (extra kwargs would raise a TypeError in verify()).
        fc = {k: v for k, v in fc.items() if isinstance(v, str) and v.strip()}
        return {"claim": str(out.get("claim") or "")[:400],
                "why": str(out.get("why") or "")[:500],
                "formal_claim": fc if fc.get("kind") else None}

    # --- the exploration loop -------------------------------------------------
    def explore(self, goal: str, *, approaches: int = 4, rounds: int = 2) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        learned = ""
        try:
            hints = self._led().hints(goal)
        except Exception:  # noqa: BLE001
            hints = ""
        for rnd in range(rounds):
            plans = self._diverge(goal, approaches, learned, hints)
            if not plans:
                history.append({"round": rnd + 1, "note": "sin enfoques (¿IA disponible?)"})
                break
            results: list[dict[str, Any]] = []
            with ThreadPoolExecutor(max_workers=self._workers,
                                    thread_name_prefix="explore") as pool:
                futs = [pool.submit(self._assemble_run, goal, a) for a in plans]
                for f in as_completed(futs):
                    try:
                        results.append(f.result())
                    except Exception:  # noqa: BLE001
                        continue
            viable = [r for r in results if r.get("found")]
            history.append({"round": rnd + 1, "approaches": len(plans),
                            "viable": len(viable),
                            "tried": [{"method": r.get("method"), "found": r.get("found"),
                                       "candidate": r.get("candidate")} for r in results]})
            if not viable:
                learned = "; ".join(f"{r.get('method')} falló ({r.get('error') or 'sin resultado'})"
                                    for r in results)[:600]
                continue
            hyp = self._synthesize(goal, viable)
            if not hyp["claim"]:
                learned = "los enfoques dieron resultados pero no se sintetizó hipótesis"
                continue
            verdict = self._probe_claim(hyp["claim"], hyp.get("formal_claim"))
            novelty = self._check_novelty(hyp["claim"])
            vd = verdict.get("verdict")
            conflict = ""
            # CONSENSUS GUARD: overturning a result that 2+ independent viable
            # approaches agree on is extraordinary. Unless the refutation is a robust,
            # reproduced counterexample, abstain to human review rather than emit a
            # decisive (and possibly false) 'refuted'.
            if vd == "refuted" and len(viable) >= 2:
                conflict = (f"refutación NO corroborada: {len(viable)} enfoques "
                            "independientes coinciden en el resultado → se degrada a "
                            "'candidato' para revisión humana, no se declara refutado")
                status, settled = "candidate", False
            else:
                settled = vd in ("verified", "refuted")
                status = "settled" if settled else "candidate"
            return self._finish(goal, {
                "goal": goal, "status": status,
                "hypothesis": hyp["claim"], "why": hyp["why"],
                "verdict": vd, "verdict_detail": verdict.get("detail"),
                "conflict": conflict or None,
                "formal": verdict.get("formal"),
                "novelty": (novelty or {}).get("verdict"),
                "viable_approaches": [{"method": v["method"], "candidate": v.get("candidate"),
                                       "tools_used": v.get("tools_used") or []}
                                      for v in viable],
                "rounds": history,
            })
        return self._finish(goal, {
            "goal": goal, "status": "inconclusive",
            "note": "no se halló una hipótesis viable en los enfoques probados",
            "rounds": history})

    def _finish(self, goal: str, result: dict[str, Any]) -> dict[str, Any]:
        """Persist the outcome to the results ledger, then return it unchanged."""
        try:
            self._led().record(goal, result)
        except Exception:  # noqa: BLE001
            pass
        return result
