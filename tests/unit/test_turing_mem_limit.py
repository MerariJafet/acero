"""Turing corre sin jaula, pero no sin techo.

Incidente real (2026-08-11, Ronda 133): un experimento que Turing generó creció
hasta 54 GiB en 35 minutos. La máquina quedó con 1.6 GiB libres y sin swap, y
hubo que matar el proceso a mano para no perder el portal ni las 5 semillas de
Caccetta–Häggkvist. `cover_growth.py` y `kmin_law.py` sí tienen guarda de
memoria; un script escrito por un LLM no la lleva, y pedirla por prompt no es un
mecanismo.

Correr sin sandbox es una decisión explícita de Merari y se mantiene. Lo que
estos tests fijan es que sin jaula ≠ sin techo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from acero.core.config import repo_root
from acero.science.turing import _default_run, mem_limit_bytes


def test_el_techo_sale_del_entorno_si_esta(monkeypatch) -> None:
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "2.5")
    assert mem_limit_bytes() == int(2.5 * 1024 ** 3)


def test_sin_entorno_el_techo_es_la_mitad_de_la_RAM(monkeypatch) -> None:
    """Fracción y no número fijo: el programa se instala en máquinas muy
    distintas y un tope absoluto sería inútil o asfixiante según cuál."""
    monkeypatch.delenv("ACERO_TURING_MEM_GB", raising=False)
    lim = mem_limit_bytes()
    with open("/proc/meminfo", encoding="ascii") as fh:
        total = next(int(l.split()[1]) for l in fh if l.startswith("MemTotal:")) * 1024
    assert lim == total // 2


def test_valor_basura_en_el_entorno_no_deja_sin_techo(monkeypatch) -> None:
    """Un typo en la variable no debe traducirse en 'sin límite'."""
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "muchos")
    assert mem_limit_bytes() > 0


def test_un_script_glotón_muere_en_vez_de_comerse_la_maquina(monkeypatch) -> None:
    """EL CASO DEL INCIDENTE: reservar sin freno. Debe fallar el hijo, no el host."""
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "0.25")
    code = ("b = []\n"
            "for _ in range(1000):\n"
            "    b.append(bytearray(50 * 1024 * 1024))\n"
            "print('NUNCA LLEGA AQUI')\n")
    r = _default_run(code, timeout_s=60)
    assert r["rc"] != 0
    assert "NUNCA LLEGA AQUI" not in r["stdout"]
    assert "MemoryError" in r["stderr"] or "Cannot allocate memory" in r["stderr"]
    # y el fallo es ÚTIL: el bucle de reparación recibe una instrucción concreta
    assert "techo de" in r["stderr"] and "lotes" in r["stderr"]
    assert r["mem_limit_bytes"] == int(0.25 * 1024 ** 3)


def test_un_script_sano_corre_igual_que_antes(monkeypatch) -> None:
    """El techo no le quita a Turing ninguna capacidad de investigar."""
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    r = _default_run("print('EVIDENCIA: 2+2 =', 2 + 2)\nprint('VEREDICTO: ok')\n",
                     timeout_s=60)
    assert r["rc"] == 0
    assert "EVIDENCIA: 2+2 = 4" in r["stdout"] and "VEREDICTO: ok" in r["stdout"]


def test_el_script_corre_como_main_y_conserva_sus_lineas(monkeypatch) -> None:
    """El lanzador no toca el fichero del LLM: `if __name__ == '__main__'` sigue
    disparando y las trazas apuntan a las líneas reales del script."""
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    r = _default_run("if __name__ == '__main__':\n    print('SOY MAIN')\n",
                     timeout_s=60)
    assert r["rc"] == 0 and "SOY MAIN" in r["stdout"]
    r2 = _default_run("x = 1\nraise ValueError('boom')\n", timeout_s=60)
    assert "line 2" in r2["stderr"] and "boom" in r2["stderr"]


def test_el_timeout_sigue_funcionando(monkeypatch) -> None:
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    r = _default_run("import time\ntime.sleep(30)\n", timeout_s=2)
    assert r["rc"] == -1 and "TIMEOUT" in r["stderr"]


@pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_AS es de POSIX")
def test_el_limite_llega_al_hijo() -> None:
    """Comprobación directa: el hijo VE el rlimit, no lo damos por hecho."""
    import os
    os.environ["ACERO_TURING_MEM_GB"] = "3"
    r = _default_run("import resource\n"
                     "print('LIM', resource.getrlimit(resource.RLIMIT_AS)[0])\n",
                     timeout_s=60)
    assert f"LIM {int(3 * 1024 ** 3)}" in r["stdout"]
    del os.environ["ACERO_TURING_MEM_GB"]


# --- cosecha de research/: lo que Turing "materializa" no puede perderse -----------
#
# Incidente real (Ronda 8, 2026-08-13): Turing corre con cwd=sandbox_efímero, así
# que un script que escribe 'research/reto50/x.json' lo deja dentro del sandbox,
# que se borra al terminar _default_run. El VEREDICTO decía OK pero Mendeleev
# recibía FileNotFoundError — el archivo existió, brevemente, en un directorio ya
# destruido. Estos tests fijan que lo que se escribe bajo research/ sobrevive.

def _limpiar(rel: str) -> None:
    dest = repo_root() / "research" / rel
    if dest.exists():
        dest.unlink()
    # limpia directorios intermedios que el test haya creado, si quedan vacíos
    for parent in dest.parents:
        if parent == repo_root() / "research" or parent == repo_root():
            break
        try:
            parent.rmdir()
        except OSError:
            break


def test_lo_escrito_bajo_research_sobrevive_al_sandbox(monkeypatch) -> None:
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    rel = "_test_cosecha/materializado.json"
    try:
        r = _default_run(
            "import os, json\n"
            "os.makedirs('research/_test_cosecha', exist_ok=True)\n"
            "json.dump({'ok': True}, open('research/_test_cosecha/materializado.json', 'w'))\n"
            "print('VEREDICTO: OK')\n",
            timeout_s=60)
        assert r["rc"] == 0 and "VEREDICTO: OK" in r["stdout"]
        dest = repo_root() / "research" / rel
        assert dest.is_file(), "el artefacto no sobrevivió al sandbox efímero"
        assert "materializado.json" in r["stderr"]  # queda anotado qué se copió
    finally:
        _limpiar(rel)


def test_sin_escritura_bajo_research_no_pasa_nada_ni_falla(monkeypatch) -> None:
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    r = _default_run("print('VEREDICTO: sin artefactos')\n", timeout_s=60)
    assert r["rc"] == 0
    assert "artefactos copiados" not in r["stderr"]


def test_la_cosecha_tambien_corre_si_hay_timeout(monkeypatch) -> None:
    """Un experimento que escribe y LUEGO cuelga no debe perder lo ya materializado."""
    monkeypatch.setenv("ACERO_TURING_MEM_GB", "1")
    rel = "_test_cosecha_timeout/parcial.json"
    try:
        r = _default_run(
            "import os, json, time\n"
            "os.makedirs('research/_test_cosecha_timeout', exist_ok=True)\n"
            "json.dump({'parcial': True}, "
            "open('research/_test_cosecha_timeout/parcial.json', 'w'))\n"
            "time.sleep(30)\n",
            timeout_s=2)
        assert r["rc"] == -1 and "TIMEOUT" in r["stderr"]
        dest = repo_root() / "research" / rel
        assert dest.is_file(), "lo escrito antes del timeout también debe cosecharse"
    finally:
        _limpiar(rel)
