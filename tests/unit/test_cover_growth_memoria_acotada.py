"""2026-08-14: `signatures` (mask->conteo) dejó de comprimir hace rato --
n_signatures/n_hard = 1.0000 desde N≈1e7 en la corrida real -- así que el
diccionario crecía ~1 a 1 con los primos y pasó de MB a ~29GB en N=2e11,
proyectando >140GB en N=1e12 (la máquina tiene 62GB). Ver el docstring de
cover_growth.py ("MEMORIA ACOTADA") para el diagnóstico completo.

Estos tests fijan que el arreglo (contadores streaming para supervivencia() +
techo SIG_CAP para signatures) da EXACTAMENTE los mismos números que el diseño
viejo por lote -- no es solo "más barato", es idéntico -- y que la migración de
un checkpoint viejo (sin 'counters') reconstruye ese estado sin perder nada.

`research/reto50/` está en .gitignore (dato de workspace, no del motor) -- este
archivo se salta solo en un clon limpio del repo, igual que
test_cover_growth_atomic_checkpoint.py."""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path

import pytest

_MODULE_PATH = (Path(__file__).resolve().parents[2] / "research" / "reto50"
                / "cover_growth.py")

pytestmark = pytest.mark.skipif(
    not _MODULE_PATH.exists(),
    reason="research/reto50/cover_growth.py no está versionado (dato de workspace, "
          "no del motor) -- ausente en un clon limpio del repo")


@pytest.fixture(scope="module")
def cg():
    spec = importlib.util.spec_from_file_location("_cover_growth_under_test_2", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _masks_sinteticas(n: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    nbits = len(_MODULE_PATH.read_text()) and 12  # nbits fijo, no depende del archivo
    return [rng.getrandbits(nbits) for _ in range(n)]


def test_streaming_da_lo_mismo_que_el_lote_con_duplicados(cg) -> None:
    """Caso con repetición real (firmas que sí colisionan) -- el caso para el
    que `supervivencia_from_signatures` fue diseñada originalmente."""
    masks = _masks_sinteticas(5000, seed=1) + [0] * 7  # fuerza algunas huérfanas
    signatures: dict[int, int] = {}
    for m in masks:
        signatures[m] = signatures.get(m, 0) + 1

    counters = cg._nuevo_estado_supervivencia()
    for m in masks:
        cg._actualizar_supervivencia(counters, m)

    esperado = cg.supervivencia_from_signatures(signatures)
    real = cg.supervivencia_from_counters(counters)
    assert real == esperado


def test_streaming_da_lo_mismo_que_el_lote_sin_duplicados(cg) -> None:
    """Caso realista de la corrida en vivo: casi ninguna firma se repite
    (ratio observado 1.0000 desde N=1e7) -- el caso que rompió el diseño
    original."""
    masks = list(range(1, 3000))  # todas distintas, ninguna colisiona
    signatures = {m: 1 for m in masks}
    counters = cg._nuevo_estado_supervivencia()
    for m in masks:
        cg._actualizar_supervivencia(counters, m)

    assert cg.supervivencia_from_counters(counters) == cg.supervivencia_from_signatures(signatures)


def test_huerfanas_cuenta_mascara_cero(cg) -> None:
    counters = cg._nuevo_estado_supervivencia()
    for m in (0, 0, 0, 5, 9):
        cg._actualizar_supervivencia(counters, m)
    surv = cg.supervivencia_from_counters(counters)
    assert surv["huerfanas"] == 3
    assert surv["total"] == 5


def test_migracion_de_checkpoint_viejo_sin_recorte(cg, monkeypatch) -> None:
    """Checkpoint viejo con pocas firmas (bajo SIG_CAP): se migra completo, sin
    recortar nada, y counters coincide con el cálculo por lote."""
    monkeypatch.setattr(cg, "log", lambda msg: None)  # no tocar el log real
    signatures = {i: 1 for i in range(1, 101)}
    st_viejo = {"sig": signatures, "n": 100, "p": 12345, "rows": [
        {"N": 12345, "n_signatures": 100}]}
    st = cg._migrar_checkpoint_viejo(dict(st_viejo))
    assert st["cap_hit_at"] is None
    assert len(st["sig"]) == 100
    assert cg.supervivencia_from_counters(st["counters"]) == \
        cg.supervivencia_from_signatures(signatures)


def test_migracion_de_checkpoint_viejo_con_recorte(cg, monkeypatch) -> None:
    """El caso real: firmas por encima del techo. La migración debe (a)
    preservar supervivencia() exacta sobre TODO el histórico, (b) recortar
    `sig` a SIG_CAP entradas para no seguir creciendo, (c) marcar cap_hit_at."""
    monkeypatch.setattr(cg, "SIG_CAP", 50)
    monkeypatch.setattr(cg, "log", lambda msg: None)  # no tocar el log real
    signatures = {i: 1 for i in range(1, 201)}  # 200 firmas > techo de 50
    st_viejo = {"sig": signatures, "n": 200, "p": 999,
                "rows": [{"N": 500, "n_signatures": 60},
                         {"N": 999, "n_signatures": 200}]}
    st = cg._migrar_checkpoint_viejo(dict(st_viejo))
    assert len(st["sig"]) == 50
    assert st["cap_hit_at"] == 500  # primer hito donde n_signatures > techo
    # supervivencia se calculó ANTES de recortar -- debe ver las 200, no las 50
    esperado = cg.supervivencia_from_signatures(signatures)
    assert cg.supervivencia_from_counters(st["counters"]) == esperado


def test_cover_sizes_intacto_para_firmas_bajo_el_techo(cg) -> None:
    """cover_sizes() no se tocó -- sigue dando el mismo resultado de siempre
    cuando hay pocas firmas (greedy + exacto por B&B)."""
    signatures = {0b001: 5, 0b010: 3, 0b100: 2, 0b011: 1}
    greedy, exact, keys = cg.cover_sizes(signatures)
    assert greedy >= 1
    assert exact is not None  # pocas firmas -> B&B sigue siendo tratable
