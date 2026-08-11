"""Vigilancia de procesos largos sin falsos positivos.

Fallo real (supervisor Erdős–Straus, 2026-08-11): `pgrep -f cover_growth.py`
devolvía PIDs en tres ticks seguidos con el cómputo YA TERMINADO. Matcheaba el
propio shell del tick —cuyo comando contiene la cadena— y un `codex exec` cuyo
prompt menciona el script dentro del catálogo de piezas. El riesgo simétrico es
el grave: creer que algo corre y no relanzarlo nunca.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

from acero.ops.procwatch import find_script, is_running


def test_no_matchea_el_propio_shell_ni_sus_ancestros() -> None:
    """El proceso de test tiene el nombre del script en su contexto y NO cuenta."""
    assert find_script("test_procwatch.py", exclude_self=True) == []


def test_detecta_un_proceso_que_de_verdad_corre_el_script(tmp_path) -> None:
    """El nombre lleva el PID del test a propósito: usar 'cover_growth.py' hacía
    que el test fallara en cuanto el cover REAL estaba corriendo — encontraba
    once procesos legítimos además del suyo. El detector acertaba; el test era el
    que confundía 'lo que yo lancé' con 'lo que hay en la máquina'."""
    nombre = f"cover_growth_test_{os.getpid()}.py"
    script = tmp_path / nombre
    script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script)])
    try:
        for _ in range(50):                      # esperar a que /proc lo publique
            hits = find_script(nombre)
            if hits:
                break
            time.sleep(0.1)
        assert [h["pid"] for h in hits] == [proc.pid]
        assert is_running(nombre) is True
    finally:
        proc.kill()
        proc.wait()
    assert find_script(nombre) == []


def test_mencionar_el_script_dentro_de_un_argumento_NO_cuenta(tmp_path) -> None:
    """El caso exacto del `codex exec`: el nombre viaja embebido en un prompt.

    Un argumento gigante que CONTIENE 'cover_growth.py' no es ejecutarlo."""
    prompt = ("Eres Turing. Usa PARI como hace research/reto50/cover_growth.py "
              "para factorizar rápido.")
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)",
                             prompt])
    try:
        time.sleep(0.4)
        pids = [h["pid"] for h in find_script("cover_growth.py")]
        assert proc.pid not in pids
    finally:
        proc.kill()
        proc.wait()


def test_ruta_completa_o_nombre_pelado_cuentan_igual(tmp_path) -> None:
    """Da lo mismo lanzarlo como `python x/y/foo.py` que desde su directorio."""
    d = tmp_path / "reto50"
    d.mkdir()
    nombre = f"kmin_law_test_{os.getpid()}.py"   # único: ver el test anterior
    script = d / nombre
    script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, nombre], cwd=str(d))
    try:
        for _ in range(50):
            hits = find_script(nombre)
            if hits:
                break
            time.sleep(0.1)
        assert [h["pid"] for h in hits] == [proc.pid]
    finally:
        proc.kill()
        proc.wait()


def test_pid_inexistente_no_revienta() -> None:
    """/proc es una carrera: un proceso puede morir entre listdir y open."""
    from acero.ops.procwatch import _ancestors, _cmdline
    assert _cmdline(os.getpid()) != []
    assert _cmdline(999_999_999) == []
    assert os.getpid() in _ancestors(os.getpid())
