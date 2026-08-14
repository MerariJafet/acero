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

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from ..core.config import repo_root
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


def mem_limit_bytes() -> int:
    """Techo de memoria para un experimento generado.

    `ACERO_TURING_MEM_GB` manda; si no, la mitad de la RAM física. Es una
    fracción y no un número fijo porque el programa se instala en máquinas muy
    distintas y un tope absoluto sería inútil o asfixiante según cuál."""
    env = os.environ.get("ACERO_TURING_MEM_GB", "").strip()
    if env:
        try:
            return int(float(env) * 1024 ** 3)
        except ValueError:
            pass
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for linea in fh:
                if linea.startswith("MemTotal:"):
                    return int(linea.split()[1]) * 1024 // 2
    except OSError:
        pass
    return 4 * 1024 ** 3          # sin /proc: conservador antes que temerario


# Lanzador: fija el límite DENTRO del hijo y luego ejecuta el script como
# __main__. Se hace así y no con preexec_fn porque el portal es multihilo y
# fork+preexec puede colgar el hijo; esto es fork-safe y además deja el script
# del LLM intacto, sin desplazar los números de línea de sus trazas.
_LANZADOR = (
    "import resource,runpy,sys;"
    "lim=int(sys.argv[1]);"
    "resource.setrlimit(resource.RLIMIT_AS,(lim,lim));"
    "runpy.run_path(sys.argv[2],run_name='__main__')"
)


def _harvest_research_outputs(sandbox_dir: str) -> list[str]:
    """Copia a la ubicación REAL cualquier archivo que el experimento haya escrito
    bajo research/ dentro de su sandbox efímero.

    El experimento corre con cwd=sandbox_dir, así que un path relativo como
    'research/reto50/x.json' aterriza dentro del sandbox, no en el proyecto real —
    y el sandbox se borra al salir del `with` de _default_run. Visto en vivo
    (Ronda 8, 2026-08-13): Turing reportaba VEREDICTO: OK con la tabla
    "materializada", pero Mendeleev recibía FileNotFoundError tres jugadas
    seguidas al intentar leerla — el archivo existió, brevemente, en un directorio
    que ya no existía. Sin esta cosecha, cualquier cosa que Turing escriba bajo
    research/ es descartada aunque el veredicto diga lo contrario."""
    src = Path(sandbox_dir) / "research"
    if not src.is_dir():
        return []
    dest_root = repo_root() / "research"
    copied: list[str] = []
    for fp in src.rglob("*"):
        # symlinks se saltan a propósito: Turing ya corre sin jaula (decisión
        # humana explícita) y puede leer cualquier archivo del sistema con una
        # ruta absoluta de todos modos, pero un symlink DENTRO del sandbox que
        # apunte fuera (p.ej. a una clave SSH) haría que la cosecha lo copiara
        # a research/, un directorio persistente y visible — sin ganar acceso
        # nuevo, evita dejar ese rastro por accidente.
        if fp.is_file() and not fp.is_symlink():
            rel = fp.relative_to(src)
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, dest)
            copied.append(str(rel))
    return copied


def _default_run(code: str, timeout_s: int) -> dict[str, Any]:
    """Corre el script con el python del venv, aislado en un dir temporal.

    DECISIÓN HUMANA EXPLÍCITA (Merari, 2026-08-10): Turing corre a PROPÓSITO con
    subprocess crudo — SIN sandbox y CON red y entorno completos — para tener todo
    el poder de investigar (instalar piezas, descargar, computar sin jaula). La
    auditoría del 10-ago marcó esto como riesgo; Merari lo ACEPTA porque corre en
    su PC de entrenamiento aislada. NO es un descuido: es una elección de diseño
    para este entorno. En un despliegue no aislado habría que enrutar por
    SubprocessRunner (como MathProbe) — ver docs/ACERO_CONSOLIDATION_DOSSIER.md §11.1.

    TECHO DE MEMORIA (2026-08-11, aprendido en vivo): un experimento generado
    creció hasta 54 GiB en 35 minutos y dejó la máquina con 1.6 GiB libres y sin
    swap; hubo que matarlo a mano para no perder el portal y las 5 semillas de
    Caccetta–Häggkvist. `cover_growth.py` y `kmin_law.py` sí tenían guarda de
    memoria, pero un script que escribe un LLM no la lleva — y no se le puede
    pedir por prompt, porque el prompt no es un mecanismo.

    Esto NO contradice la decisión de arriba: sin jaula ≠ sin techo. El límite no
    le quita a Turing ninguna capacidad de investigar; solo impide que se lleve
    por delante la máquina que lo hospeda. Y el fallo es ÚTIL: el hijo muere con
    MemoryError, el mensaje entra al bucle de reparación y el siguiente intento
    puede escribir una versión que quepa."""
    limite = mem_limit_bytes()
    with tempfile.TemporaryDirectory(prefix="acero_turing_") as td:
        path = f"{td}/experimento.py"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            r = subprocess.run([sys.executable, "-c", _LANZADOR, str(limite), path],
                               cwd=td, capture_output=True, text=True,
                               timeout=timeout_s)
            err = r.stderr[-2500:]
            if "MemoryError" in r.stderr or "Cannot allocate memory" in r.stderr:
                err += (f"\n[ACERO] el experimento superó el techo de "
                        f"{limite / 1024 ** 3:.1f} GiB. Rehazlo con menos memoria: "
                        "procesa por lotes o en streaming en vez de materializar "
                        "todo, y no acumules listas del tamaño del barrido.")
            cosechado = _harvest_research_outputs(td)
            if cosechado:
                err += f"\n[ACERO] artefactos copiados a research/: {cosechado}"
            return {"rc": r.returncode, "stdout": r.stdout[-6000:], "stderr": err,
                    "mem_limit_bytes": limite}
        except subprocess.TimeoutExpired:
            cosechado = _harvest_research_outputs(td)
            extra = f" (artefactos copiados: {cosechado})" if cosechado else ""
            return {"rc": -1, "stdout": "",
                    "stderr": f"TIMEOUT {timeout_s}s{extra}",
                    "mem_limit_bytes": limite}


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
