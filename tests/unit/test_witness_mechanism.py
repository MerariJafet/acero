"""Mecanismo del testigo: los dientes de la llave como objeto matemático.

Contexto real (Erdős–Straus, 2026-08-11). La regla minada `qr_11 == 10 ⇒ k=11`
tenía pureza 1.000 sobre 82 casos de train y falló 17 veces en holdout. La
autopsia mostró que el nivel correcto no era una propiedad de p, sino el
conjunto de residuos FABRICABLES con los divisores disponibles de (p·x)².

Estos tests fijan las dos causas de fallo, que la estadística de superficie
confundía en un solo "no abrió":
  * obstrucción de carácter — el objetivo está fuera del subgrupo generado;
    ningún presupuesto de exponentes lo arregla (y es DEMOSTRABLE).
  * presupuesto insuficiente — está dentro del subgrupo pero exige exponentes
    mayores que los disponibles.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from acero.core.workspace import workspace  # noqa: E402

_LEGACY = Path(__file__).resolve().parents[2] / "research" / "reto50"
_NUEVA = workspace() / "investigaciones" / "erdos-straus"
_MODULE_DIR = _NUEVA if (_NUEVA / "witness_mechanism.py").exists() else _LEGACY

pytestmark = pytest.mark.skipif(
    not (_MODULE_DIR / "witness_mechanism.py").exists(),
    reason="witness_mechanism.py no está versionado (dato de workspace, no del "
          "motor) -- ausente en un clon limpio del repo o sin migrar")

sys.path.insert(0, str(_MODULE_DIR))

from witness_mechanism import (  # noqa: E402
    diagnose, evaluate_orders, pieces, reachable_bounded, subgroup_closure,
    target_residue)


def test_identidad_del_objetivo_no_depende_de_la_factorizacion() -> None:
    """r_k(p) = −p·x ≡ −p²·4⁻¹ (mod k). La reformulación de Merari: el objetivo
    se calcula sin factorizar nada. `target_residue` cruza ambas vías y revienta
    si difieren, así que basta con que no lance."""
    for p, k in [(103681, 11), (1000003, 13), (75119463721, 307)]:
        r = target_residue(p, k)
        x = (p + k) // 4
        assert r == (-(p * x)) % k
        assert r == (-pow(p, 2, k) * pow(4, -1, k)) % k


def test_abrir_produce_testigo_verificado() -> None:
    """Un veredicto 'abre' entrega t y lo verifica: t | (p·x)² y t ≡ −px mod k."""
    d = diagnose(75119463721, 307)
    assert d["veredicto"] == "abre" and d["verificado"] is True
    p, k, t = 75119463721, 307, d["testigo"]
    x = (p + k) // 4
    assert (p * x) ** 2 % t == 0
    assert (t - (-(p * x))) % k == 0


def test_llave_23_no_abre_el_primo_huerfano() -> None:
    """El primo que dejó sin cover a 1e11 no se abre con llaves chicas."""
    assert diagnose(75119463721, 23)["veredicto"] != "abre"


@pytest.mark.parametrize("p", [103681, 107641, 10018201, 100006561])
def test_fallos_de_qr11_son_presupuesto_y_no_estructura(p: int) -> None:
    """Los contraejemplos de la regla `qr_11 == 10`: el subgrupo generado es TODO
    (Z/11)*, así que el objetivo es alcanzable en principio — falla solo por
    falta de multiplicidad. Y falta EXACTAMENTE el residuo objetivo."""
    d = diagnose(p, 11)
    assert d["veredicto"] == "presupuesto_insuficiente"
    assert d["n_subgrupo"] == 10                       # todo el grupo
    assert d["faltan_del_subgrupo"] == [d["objetivo"]]  # falta justo el objetivo


@pytest.mark.parametrize("p,k", [(110881, 31), (1010881, 71),
                                 (100022521, 191), (1000020961, 71)])
def test_obstruccion_de_caracter_cuadratico(p: int, k: int) -> None:
    """LEMA (elemental y demostrable, no correlación): si todo primo q | p·x es
    residuo cuadrático mod k y −px es NO-residuo, entonces k no abre p — porque
    todo divisor de (px)² es producto de esos primos, luego residuo cuadrático,
    y jamás puede ser congruente con un no-residuo.

    Estos cuatro son los fallos del holdout que NO son de presupuesto."""
    d = diagnose(p, k)
    assert d["veredicto"] == "obstruccion_estructural"

    def legendre(a: int) -> int:
        return pow(a, (k - 1) // 2, k)

    assert all(legendre(g) == 1 for _q, g, _e in pieces(p, k))
    assert legendre(target_residue(p, k)) != 1
    # el subgrupo es exactamente el de índice 2 (los residuos cuadráticos)
    assert d["n_subgrupo"] * 2 == k - 1
    # y aquí no hay presupuesto que valga: alcanzable == subgrupo
    assert d["faltan_del_subgrupo"] == []


def test_reachable_es_subconjunto_del_subgrupo() -> None:
    """Invariante estructural: acotar exponentes solo puede QUITAR residuos."""
    for p, k in [(103681, 11), (1010881, 71), (10005241, 31)]:
        assert set(reachable_bounded(p, k)) <= subgroup_closure(p, k)


def test_kpi_cuenta_intentos_no_aciertos_a_la_primera() -> None:
    """El KPI correcto: como cada candidato se verifica mecánicamente, fallar
    solo cuesta tiempo. Medir 'acertó a la primera' castigaría a un sistema que
    acierta al segundo y sería igual de útil."""
    filas = [{"p": 1, "keys": [23, 71]}, {"p": 2, "keys": [11]},
             {"p": 3, "keys": [71]}]
    res = evaluate_orders(filas, {"a": [23, 11, 71], "b": [71, 23, 11]})
    # el módulo redondea a 3 decimales para que el JSON sea legible
    assert res["a"]["media_intentos"] == pytest.approx((1 + 2 + 3) / 3, abs=1e-3)
    assert res["b"]["media_intentos"] == pytest.approx((1 + 3 + 1) / 3, abs=1e-3)
    assert res["b"]["p_exito_1"] == pytest.approx(2 / 3, abs=1e-4)
    # una llave que no abre ninguna se declara, no se esconde
    res2 = evaluate_orders(filas, {"c": [13]})
    assert res2["c"]["sin_llave_en_el_orden"] == 3
    assert res2["c"]["media_intentos"] is None


def test_mal_formada_se_declara_en_vez_de_fingir() -> None:
    """p+k no divisible por 4: la llave ni siquiera entra. No es 'no abre'."""
    p = 103681
    k = next(k for k in range(3, 40, 2) if (p + k) % 4 != 0)
    assert diagnose(p, k)["veredicto"] == "mal_formada"
