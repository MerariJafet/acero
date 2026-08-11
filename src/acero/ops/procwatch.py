"""¿Está vivo REALMENTE este cómputo largo? — sin falsos positivos.

Nace de un fallo operativo repetido: `pgrep -f cover_growth.py` devolvía PIDs en
cada tick del supervisor, y ninguno era el proceso. Matcheaba (a) el propio shell
del tick, porque el comando contiene la cadena, y (b) un `codex exec` cuyo prompt
menciona el script dentro del catálogo de piezas. Tres ticks seguidos leyeron
"vivo" sobre un proceso muerto — y el riesgo simétrico es peor: creer que algo
corre y NO relanzarlo.

La discriminación correcta no es "la línea de comandos contiene el nombre", sino
"**algún argumento ES** el script". Un prompt que lo menciona lo lleva embebido
dentro de un argumento gigante; el intérprete real lo lleva como argv propio.

`os.getpid()` y los ancestros se excluyen aparte, porque un envoltorio legítimo
(el `bash -c` que ejecuta la comprobación) sí puede tener el nombre como palabra.
"""

from __future__ import annotations

import os


def _cmdline(pid: int) -> list[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            return [a.decode("utf-8", "replace")
                    for a in fh.read().split(b"\0") if a]
    except (OSError, ValueError):
        return []


def _ancestors(pid: int) -> set[int]:
    """La cadena de padres, para no contarnos a nosotros mismos."""
    out: set[int] = set()
    cur = pid
    while cur > 1 and cur not in out:
        out.add(cur)
        try:
            with open(f"/proc/{cur}/stat", encoding="ascii") as fh:
                # el nombre del ejecutable va entre paréntesis y puede traer
                # espacios: cortar por el ÚLTIMO ')' es lo único fiable
                cur = int(fh.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return out


def find_script(script: str, *, exclude_self: bool = True) -> list[dict[str, object]]:
    """PIDs que ejecutan `script` DE VERDAD (p. ej. 'cover_growth.py').

    Un proceso cuenta solo si algún argumento termina en el nombre del script,
    no si lo menciona dentro de un argumento más largo."""
    yo = os.getpid()
    excl = _ancestors(yo) if exclude_self else set()
    encontrados = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid in excl:
            continue
        argv = _cmdline(pid)
        if not any(a == script or a.endswith("/" + script) for a in argv):
            continue
        encontrados.append({"pid": pid, "cmdline": " ".join(argv)[:200]})
    return encontrados


def is_running(script: str) -> bool:
    return bool(find_script(script))
