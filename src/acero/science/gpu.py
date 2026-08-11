"""GPU (CUDA) — preparación y regla del 90% de VRAM.

Merari tiene una NVIDIA RTX (serie 50, driver 580 instalado como librería) con
~8 GB de VRAM. El módulo del kernel NO está cargado hoy: activarlo requiere
instalar nvidia-utils y REINICIAR la PC — por eso el protocolo es:

  PROTOCOLO DE ARRANQUE (orden de Merari): antes de lanzar CUALQUIER trabajo que
  necesite la GPU, AVISAR a Merari y esperar su confirmación — él debe reiniciar
  para dejar los drivers activos. Nunca asumir que la GPU está lista.

Qué SÍ es para la GPU en ACERO (tensores de verdad):
  * Mendeleev fase neuronal: GNN / autoencoders / representation learning sobre
    los PatternCandidates y datasets grandes (PyTorch).
  * Embeddings semánticos (novedad de Hipatia a escala, dedup de literatura).
  * Bootstraps/permutaciones masivas de estabilidad sobre millones de filas.
Qué NO (y hay que resistir la tentación): z3/SMT (lógica secuencial ramificada),
factorización de enteros, DP de divisores, set-cover B&B — control irregular
donde la GPU pierde contra un buen CPU. Un solver no es un tensor.

Regla del 90% de VRAM (mismo espíritu que la RAM): `wait_for_vram()` forma el
trabajo en la FILA si la tarjeta va llena — preferimos tardar a colgar la PC.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

VRAM_FRAC_MAX = float(os.environ.get("ACERO_VRAM_FRAC", "0.90"))


def status() -> dict[str, Any]:
    """Estado honesto de la GPU: qué hay, qué falta, y el siguiente paso humano."""
    out: dict[str, Any] = {"available": False, "torch_cuda": False,
                           "driver_loaded": False, "vram_total_mb": None,
                           "vram_used_mb": None, "device": None, "next_step": ""}
    out["driver_lib"] = os.path.exists("/usr/lib/x86_64-linux-gnu/libcuda.so.1")
    out["driver_loaded"] = os.path.exists("/dev/nvidia0")
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10)
        if q.returncode == 0 and q.stdout.strip():
            name, total, used = [s.strip() for s in
                                 q.stdout.strip().splitlines()[0].split(",")]
            out.update(device=name, vram_total_mb=int(total),
                       vram_used_mb=int(used), driver_loaded=True)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError):
        pass
    try:
        import torch
        out["torch_cuda"] = bool(torch.cuda.is_available())
        if out["torch_cuda"]:
            out["device"] = torch.cuda.get_device_name(0)
            free_b, total_b = torch.cuda.mem_get_info(0)
            out["vram_total_mb"] = total_b // (1024 * 1024)
            out["vram_used_mb"] = (total_b - free_b) // (1024 * 1024)
    except Exception:  # noqa: BLE001 - sin torch ⇒ simplemente no está
        pass
    out["available"] = out["torch_cuda"] and out["driver_loaded"]
    if out["available"]:
        out["next_step"] = "lista — respetar wait_for_vram() antes de cargar"
    elif out["driver_lib"] and not out["driver_loaded"]:
        out["next_step"] = ("AVISAR A MERARI: instalar nvidia-utils y REINICIAR "
                            "la PC para cargar el driver — no lanzar nada GPU antes")
    elif not out["torch_cuda"]:
        out["next_step"] = ("instalar PyTorch con CUDA (pip install torch) tras "
                            "activar el driver")
    return out


def vram_used_frac() -> float:
    """Fracción de VRAM usada; 1.0 (presión total, conservador) si no es legible."""
    st = status()
    if not st["vram_total_mb"]:
        return 1.0
    return float(st["vram_used_mb"] or 0) / float(st["vram_total_mb"])


def wait_for_vram(max_frac: float = VRAM_FRAC_MAX, *, poll_s: float = 30.0,
                  max_wait_s: float | None = None,
                  log=print) -> bool:
    """Regla del 90% de VRAM: espera en FILA hasta que haya espacio. True si lo
    hubo; False si se agotó max_wait_s (el llamador decide, jamás forzar)."""
    t0 = time.time()
    while (frac := vram_used_frac()) > max_frac:
        if max_wait_s is not None and time.time() - t0 > max_wait_s:
            return False
        log(f"GPU en fila: VRAM al {frac:.0%} (>{max_frac:.0%}) — "
            f"reintento en {poll_s:.0f}s")
        time.sleep(poll_s)
    return True


def require_gpu_or_explain() -> tuple[bool, str]:
    """Para los ejecutores: (lista, mensaje). Si no está lista, el mensaje incluye
    el paso humano pendiente — el trabajo NO se lanza y se avisa a Merari."""
    st = status()
    if st["available"]:
        return True, f"GPU lista: {st['device']} ({st['vram_total_mb']} MB)"
    return False, (f"GPU NO disponible aún — {st['next_step']}. Trabajo en pausa "
                   "hasta confirmación humana (protocolo de aviso previo).")


# --- política de GPU: autonomía DENTRO de una caja aprobada una vez -----------------
# Revisión externa aceptada: confirmar cada trabajo a mano contradice la autonomía.
# El humano aprueba ESTA política una vez (activando el driver); dentro de ella
# ACERO trabaja solo; salir de la caja vuelve a requerir aprobación humana.
GPU_POLICY: dict[str, Any] = {
    "approved_by_human": False,       # ← Merari la aprueba al activar el driver
    "max_vram_frac": VRAM_FRAC_MAX,   # regla del 90% de VRAM
    "max_vram_mb": 6144,              # techo por trabajo (deja aire al escritorio)
    "max_duration_s": 3 * 3600,
    "max_concurrent_jobs": 1,
    "internet": False,                # los trabajos GPU corren sin red, como todo
    "approved_libraries": ["torch", "torch_geometric", "faiss",
                           "sentence_transformers"],
}


def policy_allows(job: dict[str, Any]) -> tuple[bool, str]:
    """¿Este trabajo cabe en la caja aprobada? (lista, razón). Fuera de la caja
    ⇒ (False, motivo) y el llamador debe pedir aprobación humana explícita."""
    if not GPU_POLICY["approved_by_human"]:
        return False, ("la política GPU aún no está aprobada por Merari — "
                       "activar driver (reinicio) y aprobar una vez")
    lib = str(job.get("library") or "")
    if lib not in GPU_POLICY["approved_libraries"]:
        return False, f"librería '{lib}' fuera de la política aprobada"
    if float(job.get("vram_mb") or 0) > GPU_POLICY["max_vram_mb"]:
        return False, (f"pide {job.get('vram_mb')}MB > techo "
                       f"{GPU_POLICY['max_vram_mb']}MB")
    if float(job.get("duration_s") or 0) > GPU_POLICY["max_duration_s"]:
        return False, "duración estimada excede la política"
    if job.get("internet"):
        return False, "los trabajos GPU corren sin red por política"
    return True, "dentro de la política aprobada"
