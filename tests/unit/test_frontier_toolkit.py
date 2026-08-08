"""Tests del FRONTIER TOOLKIT: paridad clásica Erdős–Straus, CH acotado y timeout duro."""
from __future__ import annotations

import time

from acero.science import formal_verify
from acero.science.frontier_toolkit import (
    caccetta_haggkvist_bounded,
    coprime_divisor_obstruction,
    egyptian3,
    erdos_straus_coverage,
    erdos_straus_coverage_refined,
    parametric_family,
)


def test_egyptian3_exact() -> None:
    x, y, z = egyptian3(4, 17)
    assert 1 / 4.25 - (1 / x + 1 / y + 1 / z) == 0 or True  # forma flotante no fiable
    from sympy import Rational
    assert Rational(4, 17) == Rational(1, x) + Rational(1, y) + Rational(1, z)


def test_familia_tipo_ii_cubre_13_mod_24() -> None:
    """La clase 13 mod 24 exige el término producto clásico (Mordell, n≡5 mod 8)."""
    fam = parametric_family(13, 24)
    assert fam and fam["verified"]
    assert "n*(n" in fam["y"] or "n*(n" in fam["z"]      # término producto presente


def test_clase_dura_1_mod_24_no_tiene_familia() -> None:
    """1 mod 24 contiene los cuadrados duros mod 840: NO debe salir familia."""
    assert parametric_family(1, 24) is None


def test_frontera_mod_24_es_exactamente_1() -> None:
    cov = erdos_straus_coverage(24)
    assert sorted(cov["frontier"]) == [1]


def test_paridad_clasica_mod_840() -> None:
    """El hito: los residuos duros tras refinar a mod 840 son EXACTAMENTE los
    6 cuadrados clásicos — cobertura de Mordell reproducida y probada."""
    res = erdos_straus_coverage_refined(24, 840)
    assert res["hard_residues"] == [1, 121, 169, 289, 361, 529]


def test_caccetta_haggkvist_caso_apretado_n9() -> None:
    """n=9 (múltiplo de 3) NO está implicado por Hladký–Král'–Norin (0.3465n>3):
    el caso apretado donde el lema mecanizado aporta de verdad."""
    r = caccetta_haggkvist_bounded(9, 3, timeout_ms=120000)
    assert r["result"] == "proved" and r["min_outdeg"] == 3


def test_obstruccion_coprimalidad_z3() -> None:
    assert coprime_divisor_obstruction() is True


def test_formal_verify_timeout_duro(monkeypatch) -> None:
    """Un dispatch colgado se mata y devuelve unknown/timeout (bug Cuboide)."""
    monkeypatch.setattr(formal_verify, "_verify_dispatch",
                        lambda kind, **kw: time.sleep(60))
    t = time.time()
    r = formal_verify.verify("identity", timeout_s=2, lhs="x", rhs="x")
    assert r["result"] == "unknown" and "timeout" in r["detail"]
    assert time.time() - t < 10


def test_formal_verify_sigue_probando_y_refutando() -> None:
    assert formal_verify.verify("identity", lhs="(x+1)**2",
                                rhs="x**2+2*x+1")["result"] == "proved"
    assert formal_verify.verify("identity", lhs="x**2",
                                rhs="x**3")["result"] == "refuted"
