"""TURING — el constructor experimental del Consejo.

Recibe una chispa de Ramanujan y las piezas que eligió el matemático, y hace lo que
haría un hacker-matemático: ESCRIBE el experimento en Python, lo corre, lee el error,
lo repara y vuelve — durante horas si hace falta. Si le falta una pieza, la pide al
TOOLBOX (pip/docker) o la construye él mismo en Python dentro del experimento.

Honestidad:
- El código de Turing produce EVIDENCIA (o pruebas mecánicas si usa z3/sympy y lo
  declara); jamás su salida se toma como teorema sin pasar por Gödel/Aristóteles.
- Cada ronda queda registrada (código, salida, reparación) — trazabilidad total.
- El presupuesto es de TIEMPO (horas), no de intentos: la actitud es "y si sí".
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

from . import toolbox

TURING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "razonamiento": {"type": "string",
                         "description": "qué va a probar este experimento y por qué"},
        "necesita_piezas": {"type": "array", "items": {"type": "string"},
                            "description": "piezas del TOOLBOX que faltan (se instalarán)"},
        "code": {"type": "string",
                 "description": "script python COMPLETO y autocontenido"},
        "criterio_exito": {"type": "string",
                           "description": "qué línea/valor de salida contaría como señal"},
    },
    "required": ["razonamiento", "necesita_piezas", "code", "criterio_exito"],
    "additionalProperties": False,     # Codex exige esquemas estrictos
}

_TURING_SYS = """Eres Turing en el Consejo de ACERO: matemático que programa. Te dan
una CHISPA (idea de ataque) y las PIEZAS elegidas. Escribe UN script python completo
que ejecute el primer experimento decisivo de esa idea.

Reglas del constructor:
- Aritmética EXACTA cuando el claim lo exige (Fraction/sympy/gmpy2, jamás flotantes
  para afirmar igualdades). z3 `unsat` sí es prueba mecánica y puedes declararla.
- Para usar Sage: from acero.science.toolbox import run_sage; run_sage(codigo_sage)
  — corre en contenedor sin red y devuelve stdout.
- Imprime líneas de evidencia claras: EVIDENCIA: ..., VEREDICTO: ... al final.
- Si te falta una pieza instalable, decláralo en necesita_piezas (se instalará y
  volverás a intentar). Si no existe, CONSTRÚYELA en python dentro del script.
- Sin red en el experimento (los datos se calculan, no se descargan).
- El script debe terminar solo (sin input()) y aguantar su propio timeout."""

_REPAIR_SYS = """Tu experimento anterior FALLÓ. Repara el script (completo, no un
parche) conservando el objetivo y el criterio de éxito. Si el error revela que el
enfoque es imposible, di por qué en razonamiento y devuelve un experimento
alternativo más simple que aún ataque la chispa."""


def _default_run(code: str, timeout_s: int) -> dict[str, Any]:
    """Corre el script con el python del venv, aislado en un dir temporal."""
    with tempfile.TemporaryDirectory(prefix="acero_turing_") as td:
        path = f"{td}/experimento.py"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            r = subprocess.run([sys.executable, path], cwd=td, capture_output=True,
                               text=True, timeout=timeout_s)
            return {"rc": r.returncode, "stdout": r.stdout[-6000:],
                    "stderr": r.stderr[-2500:]}
        except subprocess.TimeoutExpired:
            return {"rc": -1, "stdout": "", "stderr": f"TIMEOUT {timeout_s}s"}


class TuringBuilder:
    """Bucle construir→correr→leer→reparar con presupuesto de horas."""

    def __init__(self, provider: Any,
                 run_fn: Callable[[str, int], dict[str, Any]] | None = None,
                 ensure_fn: Callable[[str], dict[str, Any]] | None = None) -> None:
        self._provider = provider
        self._run = run_fn or _default_run
        self._ensure = ensure_fn or toolbox.ensure

    def build_and_run(self, chispa: dict[str, Any], piezas: list[str],
                      budget_s: int = 3600, round_timeout_s: int = 3600,
                      on_event: Callable[[str, dict[str, Any]], None] | None = None,
                      ) -> dict[str, Any]:
        """chispa: idea de Ramanujan (chispa/plan/primer_experimento). piezas: las que
        eligió el matemático. Itera hasta señal, refutación clara o fin de presupuesto."""
        t0 = time.time()
        cat = toolbox.catalog_text()
        rounds: list[dict[str, Any]] = []
        prompt = (
            f"{_TURING_SYS}\n\nCHISPA:\n{chispa.get('chispa', '')}\n"
            f"PLAN:\n{chispa.get('plan', '')}\n"
            f"PRIMER EXPERIMENTO SUGERIDO:\n{chispa.get('primer_experimento', '')}\n"
            f"PIEZAS ELEGIDAS: {', '.join(piezas)}\n\nCATÁLOGO:\n{cat}"
        )
        last_fail = ""
        while time.time() - t0 < budget_s:
            full = prompt if not last_fail else (
                f"{prompt}\n\n{_REPAIR_SYS}\n\nFALLO ANTERIOR:\n{last_fail}")
            try:
                plan = self._provider.complete_json(full, TURING_SCHEMA,
                                                    temperature=0.3)
            except Exception as exc:  # noqa: BLE001 - provider caído: honesto y fuera
                return {"status": "provider_error", "detail": str(exc)[:200],
                        "rounds": rounds}
            for pieza in plan.get("necesita_piezas") or []:
                got = self._ensure(pieza)
                if on_event:
                    on_event("pieza", {"pieza": pieza, **got})
            remaining = int(budget_s - (time.time() - t0))
            if remaining <= 5:
                break
            res = self._run(plan["code"], min(round_timeout_s, remaining))
            entry = {"razonamiento": plan.get("razonamiento", ""),
                     "criterio_exito": plan.get("criterio_exito", ""),
                     "code": plan["code"], **res}
            rounds.append(entry)
            if on_event:
                on_event("ronda", {k: entry[k] for k in
                                   ("razonamiento", "rc", "stdout", "stderr")})
            if res["rc"] == 0 and "VEREDICTO" in res["stdout"]:
                verdict = [ln for ln in res["stdout"].splitlines()
                           if ln.startswith("VEREDICTO")]
                return {"status": "completed", "verdict": verdict[-1],
                        "evidence": [ln for ln in res["stdout"].splitlines()
                                     if ln.startswith("EVIDENCIA")],
                        "rounds": rounds,
                        "elapsed_s": round(time.time() - t0, 1)}
            last_fail = (f"rc={res['rc']}\nSTDOUT:\n{res['stdout'][-1500:]}\n"
                         f"STDERR:\n{res['stderr'][-1500:]}")
        return {"status": "budget_exhausted", "rounds": rounds,
                "elapsed_s": round(time.time() - t0, 1)}
