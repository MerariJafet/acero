"""TOOLBOX — el catálogo de piezas de LEGO matemáticas de ACERO.

Cada herramienta es una PIEZA con capacidades declaradas en lenguaje que un agente
puede leer y combinar ("¿y si junto curvas elípticas con el barrido de residuos?").
El catálogo sabe qué está instalado, qué falta y CÓMO conseguirlo (pip/docker), y
ofrece `ensure()` para que Turing pida piezas nuevas en caliente.

Honestidad: tener la pieza no es saber usarla — cada capability describe QUÉ decide
la herramienta (prueba real vs evidencia), para que el flujo nunca confunda niveles.
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
from typing import Any

# --- el catálogo -------------------------------------------------------------------
# check: nombre de módulo importable | "docker:IMAGEN" | "own" (módulo propio ACERO)
TOOLS: dict[str, dict[str, Any]] = {
    "sympy": {
        "check": "sympy", "install": ("pip", "sympy"), "nivel": "prueba-simbólica",
        "capacidades": [
            "identidades/desigualdades/límites/sumas simbólicas (prueba real si cierra)",
            "simplificación exacta, teoría de números básica (factor, totient, primos)",
        ],
    },
    "z3": {
        "check": "z3", "install": ("pip", "z3-solver"), "nivel": "prueba-mecánica",
        "capacidades": [
            "SMT/SAT: `unsat` = prueba mecánica de imposibilidad (combinatoria finita)",
            "casos acotados de conjeturas (grafos, aritmética modular) con WLOG sanos",
        ],
    },
    "cypari2": {
        "check": "cypari2", "install": ("pip", "cypari2"), "nivel": "cálculo-experto",
        "capacidades": [
            "curvas elípticas: rango analítico, puntos, ap, conductores (PARI/GP)",
            "formas modulares, L-funciones, cuerpos de números, aritmética veloz",
        ],
    },
    "python-flint": {
        "check": "flint", "install": ("pip", "python-flint"), "nivel": "cálculo-experto",
        "capacidades": [
            "polinomios/matrices exactos ultrarrápidos (FLINT), primalidad probada",
            "aritmética de precisión arbitraria con cotas de error rigurosas (arb)",
        ],
    },
    "gmpy2": {
        "check": "gmpy2", "install": ("pip", "gmpy2"), "nivel": "cálculo-experto",
        "capacidades": ["enteros GMP gigantes, next_prime, is_prime, potencias modulares"],
    },
    "numpy": {
        "check": "numpy", "install": ("pip", "numpy"), "nivel": "evidencia-numérica",
        "capacidades": ["álgebra lineal numérica, barridos vectorizados masivos"],
    },
    "scipy": {
        "check": "scipy", "install": ("pip", "scipy"), "nivel": "evidencia-numérica",
        "capacidades": ["optimización, estadística, integración numérica"],
    },
    "networkx": {
        "check": "networkx", "install": ("pip", "networkx"), "nivel": "evidencia-numérica",
        "capacidades": ["grafos: generación, invariantes, búsqueda de contraejemplos"],
    },
    "mpmath": {
        "check": "mpmath", "install": ("pip", "mpmath"), "nivel": "evidencia-numérica",
        "capacidades": ["flotantes de precisión arbitraria, funciones especiales"],
    },
    "sage": {
        "check": "docker:sagemath/sagemath", "install": ("docker", "sagemath/sagemath"),
        "nivel": "cálculo-experto",
        "capacidades": [
            "TODO Sage vía contenedor: geometría aritmética, grupos, combinatoria,",
            "curvas/abelianas, teoría de Galois — run_sage(codigo) lo ejecuta jaulado",
        ],
    },
    "gpu-cuda": {
        "check": "own:acero.science.gpu", "install": None,
        "nivel": "cálculo-experto",
        "capacidades": [
            "GPU NVIDIA (~8GB VRAM) para TENSORES: GNN/autoencoders de Mendeleev,",
            "embeddings, bootstraps masivos. NO para z3/factorización/DP (lógica",
            "irregular: la GPU pierde ahí). PROTOCOLO: gpu.status() y si no está",
            "lista, AVISAR a Merari (debe reiniciar la PC para el driver) — jamás",
            "lanzar sin su confirmación. Regla del 90% de VRAM: wait_for_vram()",
            "antes de cargar (fila, no competencia).",
        ],
    },
    "sat_escalation": {
        "check": "own:acero.science.sat_escalation", "install": None,
        "nivel": "prueba-mecánica",
        "capacidades": [
            "ESCALERA para casos finitos: directo → portafolio de semillas →",
            "cube-and-conquer paralelo (partición completa ⇒ prueba sin suerte);",
            "usar escalate(encoder) con un encoder Z3 importable; ch_encoder(n,k)"
            " ya registrado",
        ],
    },
    "frontier_toolkit": {
        "check": "own:acero.science.frontier_toolkit", "install": None,
        "nivel": "prueba-simbólica",
        "capacidades": [
            "familias paramétricas verificadas por período modular (Erdős–Straus…)",
            "coberturas por clases de residuos; casos finitos de CH k=3 por Z3",
        ],
    },
    "math_probe": {
        "check": "own:acero.science.math_probe", "install": None,
        "nivel": "evidencia-numérica",
        "capacidades": ["probador experimental: codegen+sandbox+repair sobre un claim"],
    },
    "formal_verify": {
        "check": "own:acero.science.formal_verify", "install": None,
        "nivel": "prueba-simbólica",
        "capacidades": ["verificador formal con timeout duro (identity/inequality/…)"],
    },
    "novelty_check": {
        "check": "own:acero.discovery.novelty_check", "install": None,
        "nivel": "literatura",
        "capacidades": ["Hipatia: ¿ya se hizo? multi-fuente con DOIs (anti-Erdősgate)"],
    },
}


def _is_available(check: str) -> bool:
    if check.startswith("docker:"):
        img = check.split(":", 1)[1]
        if not shutil.which("docker"):
            return False
        try:
            out = subprocess.run(["docker", "image", "inspect", img],
                                 capture_output=True, timeout=20)
            return out.returncode == 0
        except Exception:  # noqa: BLE001
            return False
    name = check.split(":", 1)[1] if check.startswith("own:") else check
    try:
        importlib.import_module(name)
        return True
    except Exception:  # noqa: BLE001
        return False


def inventory() -> dict[str, Any]:
    """Estado real del taller: qué piezas hay, cuáles faltan y cómo se consiguen."""
    have, missing = [], []
    for name, spec in TOOLS.items():
        entry = {"name": name, "nivel": spec["nivel"],
                 "capacidades": spec["capacidades"]}
        if _is_available(spec["check"]):
            have.append(entry)
        else:
            method = spec.get("install")
            entry["install"] = (f"{method[0]}:{method[1]}" if method else "propio")
            missing.append(entry)
    return {"available": have, "missing": missing}


def catalog_text() -> str:
    """El catálogo en texto para prompts de agentes (Ramanujan/Turing lo leen)."""
    inv = inventory()
    lines = ["PIEZAS DISPONIBLES:"]
    for t in inv["available"]:
        lines.append(f"- {t['name']} [{t['nivel']}]: " + "; ".join(t["capacidades"]))
    if inv["missing"]:
        lines.append("PIEZAS FALTANTES (se pueden conseguir):")
        for t in inv["missing"]:
            lines.append(f"- {t['name']} ({t.get('install')}): "
                         + "; ".join(t["capacidades"]))
    return "\n".join(lines)


def ensure(name: str, timeout_s: int = 600) -> dict[str, Any]:
    """Consigue una pieza faltante (pip install o docker pull). Turing la llama cuando
    el matemático dice 'para esto me falta X'. Honesto: reporta éxito/fracaso real."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"ok": False, "detail": f"pieza desconocida: {name}"}
    if _is_available(spec["check"]):
        return {"ok": True, "detail": "ya estaba instalada"}
    method = spec.get("install")
    if not method:
        return {"ok": False, "detail": "pieza propia de ACERO — no se instala"}
    kind, target = method
    try:
        if kind == "pip":
            import sys
            r = subprocess.run([sys.executable, "-m", "pip", "install",
                                "--no-input", target],
                               capture_output=True, text=True, timeout=timeout_s)
        elif kind == "docker":
            r = subprocess.run(["docker", "pull", target],
                               capture_output=True, text=True, timeout=timeout_s)
        else:
            return {"ok": False, "detail": f"método no soportado: {kind}"}
        ok = r.returncode == 0 and _is_available(spec["check"])
        return {"ok": ok, "detail": (r.stdout + r.stderr)[-400:]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:200]}


def run_sage(code: str, timeout_s: int = 300) -> dict[str, Any]:
    """Ejecuta código Sage en el contenedor oficial, SIN red (jaula como acero-agent).
    Devuelve stdout/stderr/rc — evidencia de cálculo experto, no prueba formal salvo
    que Sage emita una certificación explícita."""
    if not _is_available("docker:sagemath/sagemath"):
        return {"ok": False, "detail": "imagen sagemath/sagemath no disponible"}
    import os
    import tempfile
    # el entrypoint del contenedor pasa los args por `bash -c` (rompe el quoting):
    # montamos el código como archivo .sage de solo-lectura y lo ejecutamos.
    with tempfile.NamedTemporaryFile("w", suffix=".sage", prefix="acero_sage_",
                                     dir="/tmp", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(code + "\n")
        path = fh.name
    os.chmod(path, 0o644)                      # el usuario 'sage' del contenedor lee
    try:
        r = subprocess.run(
            ["docker", "run", "--rm", "--network", "none",
             "-v", f"{path}:/tmp/run.sage:ro", "sagemath/sagemath",
             "sage", "/tmp/run.sage"],
            capture_output=True, text=True, timeout=timeout_s)
        return {"ok": r.returncode == 0, "stdout": r.stdout[-4000:],
                "stderr": r.stderr[-1500:], "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": f"timeout {timeout_s}s"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:200]}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
