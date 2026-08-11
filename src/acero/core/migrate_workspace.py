"""Sacar los datos de dentro del programa, sin perder nada y sin romper nada.

Antes de esta migración el repositorio cargaba ~35 GB de resultados
(`research/artifacts`), 442 MB de checkpoints (`research/reto50`) y la base del
ledger (`acero_data/`) — todo fuera de git pero DENTRO de la carpeta del
programa. Reclonar, mover o borrar el repo se llevaba por delante meses de
trabajo, y publicar el motor obligaba a decidir archivo por archivo qué era
código y qué era nuestra investigación.

DOS GARANTÍAS, porque aquí se mueven datos irreemplazables:

1. **Nunca sobre un sistema vivo.** Si el portal o un cómputo largo están
   corriendo, la base está abierta y con WAL; moverla deja el estado partido.
   `plan()` lo detecta y `apply()` se niega salvo orden explícita.
2. **Nunca machaca.** Si el destino ya existe, ese paso se marca en conflicto y
   se omite. Preferimos una migración a medias y declarada que una pérdida
   silenciosa.

El plan se calcula y se puede imprimir ANTES de tocar disco (`--dry-run`), que
es lo único razonable cuando el paso 1 mueve 35 GB.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .workspace import ensure_workspace, workspace

# origen (relativo al repo) → destino (relativo al espacio de trabajo).
# Lo que NO está aquí se queda: es programa. `research/TOOLBOX.md` (el catálogo
# LEGO) y `research/templates` son activos del motor, no resultados.
MAPA: dict[str, str] = {
    "acero_data": "datos",
    "research/artifacts": "resultados/artifacts",
    "research/cache": "datos/cache",
    "research/datasets": "datos/datasets",
    "research/loop": "datos/loop",
    "research/registry": "datos/registry",
    "research/selfimprove": "datos/selfimprove",
    "research/projects": "investigaciones/proyectos",
    "research/reto50": "investigaciones/erdos-straus",
    "research/calibration.json": "datos/calibration.json",
}

# Si alguno de estos corre, la migración es insegura: tienen la base o los
# artefactos abiertos.
PROCESOS_BLOQUEANTES = ("cover_growth.py", "kmin_law.py", "masterkey.py")


@dataclass
class Paso:
    origen: Path
    destino: Path
    bytes: int
    estado: str          # "listo" | "conflicto" | "ausente"
    motivo: str = ""


@dataclass
class Plan:
    pasos: list[Paso] = field(default_factory=list)
    bloqueos: list[str] = field(default_factory=list)

    @property
    def seguro(self) -> bool:
        return not self.bloqueos

    @property
    def bytes_a_mover(self) -> int:
        return sum(p.bytes for p in self.pasos if p.estado == "listo")

    def resumen(self) -> str:
        lineas = []
        for p in self.pasos:
            marca = {"listo": "→", "conflicto": "✗", "ausente": "·"}[p.estado]
            lineas.append(f"  {marca} {p.origen.name:<22} {_humano(p.bytes):>9}  "
                          f"{p.destino}{(' — ' + p.motivo) if p.motivo else ''}")
        total = f"\nTOTAL a mover: {_humano(self.bytes_a_mover)}"
        if self.bloqueos:
            total += "\n\nBLOQUEADO — hay procesos usando estos datos:\n" + \
                     "\n".join(f"  · {b}" for b in self.bloqueos)
        return "\n".join(lineas) + total


def _humano(n: int) -> str:
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unidad == "TB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024.0
    return f"{n:.1f} TB"


def _tamano(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    total = 0
    for hijo in p.rglob("*"):
        try:
            if hijo.is_file() and not hijo.is_symlink():
                total += hijo.stat().st_size
        except OSError:            # carrera: el fichero puede desaparecer
            continue
    return total


def _procesos_vivos() -> list[str]:
    from ..ops.procwatch import find_script
    vivos = []
    for script in PROCESOS_BLOQUEANTES:
        for hit in find_script(script):
            vivos.append(f"{script} (pid {hit['pid']})")
    return vivos


def _portal_vivo(repo: Path) -> bool:
    """El portal mantiene la base abierta; los ficheros -wal/-shm lo delatan.

    Se mira el disco y no una lista de procesos porque el portal puede lanzarse
    de muchas formas (cli, uvicorn, systemd) y lo que importa no es cómo se
    llama sino si la base está en uso."""
    base = repo / "acero_data" / "acero.sqlite"
    return base.with_suffix(".sqlite-wal").exists() or \
        base.with_suffix(".sqlite-shm").exists()


def _colisiones(origen: Path, destino: Path) -> list[str]:
    """Qué se machacaría al fusionar `origen` dentro de `destino`.

    Que el destino EXISTA no es conflicto: `ensure_workspace()` crea el esqueleto
    (datos/, resultados/…) antes de mover, así que 'datos' siempre está ahí. El
    conflicto real es que un nombre concreto ya esté ocupado — o que el destino
    sea un fichero donde esperábamos carpeta."""
    if not destino.exists():
        return []
    if destino.is_file() or origen.is_file():
        return [destino.name]
    return sorted(h.name for h in origen.iterdir() if (destino / h.name).exists())


def plan(repo: Path, destino: Path | None = None) -> Plan:
    """Calcula el traslado SIN tocar disco."""
    raiz = destino or workspace()
    pl = Plan()
    if _portal_vivo(repo):
        pl.bloqueos.append("el portal tiene la base abierta (existe acero.sqlite-wal): "
                           "párala antes de migrar o el estado queda partido")
    pl.bloqueos.extend(_procesos_vivos())
    for rel_origen, rel_destino in MAPA.items():
        origen = repo / rel_origen
        dest = raiz / rel_destino
        if not origen.exists():
            pl.pasos.append(Paso(origen, dest, 0, "ausente"))
            continue
        choques = _colisiones(origen, dest)
        if choques:
            pl.pasos.append(Paso(origen, dest, _tamano(origen), "conflicto",
                                 f"ya existe en destino ({', '.join(choques[:3])}); "
                                 "se omite para no machacar"))
            continue
        pl.pasos.append(Paso(origen, dest, _tamano(origen), "listo"))
    return pl


def apply(pl: Plan, *, forzar: bool = False) -> list[Paso]:
    """Ejecuta el plan. Devuelve los pasos realmente movidos.

    `forzar` existe para el caso legítimo de un WAL huérfano tras un corte de
    luz, no para atropellar un ciclo vivo — por eso hay que pedirlo a mano."""
    if pl.bloqueos and not forzar:
        raise RuntimeError("migración bloqueada:\n" + "\n".join(pl.bloqueos))
    ensure_workspace()
    movidos = []
    for paso in pl.pasos:
        if paso.estado != "listo":
            continue
        paso.destino.parent.mkdir(parents=True, exist_ok=True)
        if paso.destino.is_dir() and paso.origen.is_dir():
            # fusionar, no anidar: mover 'acero_data' sobre un 'datos' existente
            # con shutil.move a secas crearía 'datos/acero_data'
            for hijo in list(paso.origen.iterdir()):
                shutil.move(str(hijo), str(paso.destino / hijo.name))
            paso.origen.rmdir()
        else:
            shutil.move(str(paso.origen), str(paso.destino))
        movidos.append(paso)
    return movidos
