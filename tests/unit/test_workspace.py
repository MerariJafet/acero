"""El programa y lo que el programa produce viven separados.

Decisión de Merari (2026-08-11): el repositorio se publica para que cualquiera lo
use en SUS investigaciones, así que solo debe contener el motor. Antes de esto
había ~35 GB de resultados y la base del ledger dentro de la carpeta del
programa — fuera de git, pero físicamente dentro: reclonar o mover el repo se
llevaba meses de trabajo por delante.
"""

from __future__ import annotations

import pytest

from acero.core.migrate_workspace import MAPA, apply, plan
from acero.core.workspace import SUBDIRS, ensure_workspace, workspace, wpath


def test_ACERO_HOME_manda_sobre_el_defecto(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "otro sitio"))
    assert workspace() == tmp_path / "otro sitio"
    monkeypatch.delenv("ACERO_HOME")
    assert workspace().name == "ACERO"


def test_la_raiz_NO_depende_de_donde_este_el_repo(tmp_path, monkeypatch) -> None:
    """Dos clones del programa deben poder compartir espacio de trabajo, y mover
    el repo no debe perder datos. Por eso no se resuelve relativo al repo."""
    monkeypatch.delenv("ACERO_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    uno = workspace()
    sub = tmp_path / "clon"
    sub.mkdir()
    monkeypatch.chdir(sub)
    assert workspace() == uno


def test_ensure_crea_el_arbol_y_explica_cada_carpeta(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    raiz = ensure_workspace()
    for nombre in SUBDIRS:
        assert (raiz / nombre).is_dir()
    leeme = (raiz / "LEEME.md").read_text(encoding="utf-8")
    for nombre in SUBDIRS:
        assert nombre in leeme          # nadie debe encontrar una carpeta muda


def test_ensure_es_idempotente_y_repone_el_leeme(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    raiz = ensure_workspace()
    (raiz / "investigaciones" / "mia").mkdir()
    (raiz / "LEEME.md").unlink()
    ensure_workspace()
    assert (raiz / "investigaciones" / "mia").is_dir()    # no destruye
    assert (raiz / "LEEME.md").exists()                   # repone


def test_wpath_crea_el_padre_de_un_fichero(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    p = wpath("datos", "sub", "acero.sqlite")
    assert p.parent.is_dir() and not p.exists()
    d = wpath("investigaciones", "erdos")
    assert d.is_dir()


def _sin_procesos() -> list[str]:
    """Estos tests prueban el PLANIFICADOR, no qué corre en la máquina.

    Sin esto fallaban en cuanto se lanzaba un cover_growth de verdad: el plan
    detectaba el proceso real —correctamente— y se declaraba bloqueado. Un test
    unitario que depende del estado del sistema no prueba lo que dice probar; el
    bloqueo por proceso vivo tiene su propio test, con la señal inyectada."""
    return []


def test_un_computo_largo_vivo_bloquea_la_migracion(tmp_path, monkeypatch) -> None:
    """La otra mitad: cuando SÍ hay un cómputo corriendo, se niega."""
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    repo = _repo_falso(tmp_path)
    pl = plan(repo, vivos_fn=lambda: ["cover_growth.py (pid 4242)"])
    assert not pl.seguro and "4242" in pl.bloqueos[0]
    with pytest.raises(RuntimeError, match="bloqueada"):
        apply(pl)


def _repo_falso(tmp_path):
    repo = tmp_path / "repo"
    (repo / "acero_data").mkdir(parents=True)
    (repo / "acero_data" / "acero.sqlite").write_bytes(b"x" * 100)
    (repo / "research" / "reto50").mkdir(parents=True)
    (repo / "research" / "reto50" / "masterkey.json").write_bytes(b"y" * 50)
    (repo / "research" / "TOOLBOX.md").write_text("catálogo LEGO", encoding="utf-8")
    return repo


def test_migracion_mueve_datos_y_deja_los_activos_del_programa(tmp_path,
                                                               monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    repo = _repo_falso(tmp_path)
    pl = plan(repo, vivos_fn=_sin_procesos)
    assert pl.seguro and pl.bytes_a_mover == 150
    apply(pl)
    ws = workspace()
    assert (ws / "datos" / "acero.sqlite").exists()
    assert (ws / "investigaciones" / "erdos-straus" / "masterkey.json").exists()
    assert not (repo / "acero_data").exists()
    # el catálogo LEGO es motor, no resultado: se queda
    assert (repo / "research" / "TOOLBOX.md").exists()
    assert "TOOLBOX" not in " ".join(MAPA)


def test_no_migra_con_la_base_abierta(tmp_path, monkeypatch) -> None:
    """El WAL delata que el portal está usando la base. Mover ahí parte el estado
    en dos — y con un ciclo vivo encima, eso es perder la ronda."""
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    repo = _repo_falso(tmp_path)
    (repo / "acero_data" / "acero.sqlite-wal").write_bytes(b"")
    pl = plan(repo, vivos_fn=_sin_procesos)
    assert not pl.seguro and "wal" in pl.bloqueos[0].lower()
    with pytest.raises(RuntimeError, match="bloqueada"):
        apply(pl)
    assert (repo / "acero_data" / "acero.sqlite").exists()   # intacto
    apply(pl, forzar=True)                                    # salida explícita
    assert (workspace() / "datos" / "acero.sqlite").exists()


def test_destino_existente_se_declara_en_conflicto_y_no_machaca(tmp_path,
                                                                monkeypatch) -> None:
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    repo = _repo_falso(tmp_path)
    previo = workspace() / "investigaciones" / "erdos-straus"
    previo.mkdir(parents=True)
    (previo / "masterkey.json").write_bytes(b"VALIOSO")
    pl = plan(repo, vivos_fn=_sin_procesos)
    apply(pl)
    assert (previo / "masterkey.json").read_bytes() == b"VALIOSO"
    assert (repo / "research" / "reto50").exists()      # el origen sigue ahí
    conflictos = [p for p in pl.pasos if p.estado == "conflicto"]
    assert len(conflictos) == 1 and "machacar" in conflictos[0].motivo


def test_plan_no_toca_disco(tmp_path, monkeypatch) -> None:
    """Con 35 GB en juego, mirar antes de mover no es opcional."""
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "ws"))
    repo = _repo_falso(tmp_path)
    pl = plan(repo, vivos_fn=_sin_procesos)
    assert (repo / "acero_data" / "acero.sqlite").exists()
    assert not (tmp_path / "ws").exists()
    assert "acero_data" in pl.resumen() and "TOTAL a mover" in pl.resumen()
