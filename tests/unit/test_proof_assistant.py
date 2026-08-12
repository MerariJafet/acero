"""Tests for Gödel — the Z3-backed mechanized prover (beyond sympy)."""

from __future__ import annotations

import logging

import pytest

from acero.science import proof_assistant as ga

z3 = pytest.importorskip("z3")  # these need the Z3 backend installed


def test_universal_integer_inequality_is_proved():
    # ∀ integer n: n*n >= 0  — sympy-hard as a *logic* statement, trivial for Z3
    r = ga.prove("int_forall", expr="n*n >= 0", vars=["n"])
    assert r["result"] == "proved" and r["backend"] == "z3"


def test_false_universal_is_refuted_with_counterexample():
    r = ga.prove("int_forall", expr="n >= 0", vars=["n"])
    assert r["result"] == "refuted" and "counterexample" in r


def test_universal_under_hypotheses():
    # ∀ n,m: (n>=0 ∧ m>=0) → n+m >= 0   — quantified reasoning with assumptions
    r = ga.prove("int_forall", expr="n + m >= 0", vars=["n", "m"],
                 assume=["n >= 0", "m >= 0"])
    assert r["result"] == "proved"


def test_boolean_tautology_is_proved():
    r = ga.prove("bool_forall", expr="Or(a, Not(a))", vars=["a"], sort="bool")
    assert r["result"] == "proved"


def test_satisfiable_witness():
    r = ga.prove("int_exists", expr="And(n > 5, n < 8)", vars=["n"])
    assert r["result"] == "proved" and "witness" in r


def test_bad_expression_is_unknown_not_crash():
    r = ga.prove("int_forall", expr="))(", vars=["n"])
    assert r["result"] == "unknown"
    assert ga.prove("nonsense_kind", expr="n>=0", vars=["n"])["result"] == "unknown"


# --- el solve corre EN UN HIJO, con techo y latido -------------------------
# z3.Solver.check() es una llamada C++ bloqueante: no se interrumpe desde Python ni
# emite señal. In-process, un solo solve secuestra el ciclo entero del Consejo sin
# dejar rastro — se observó en vivo un check() de 13.24 h de CPU (2.4 GB) que dejó a
# la Ronda 4 congelada en la jugada 51, indistinguible de un cuelgue salvo mirando
# /proc. Aquí se fija que eso no puede repetirse en silencio.

def test_solve_eterno_se_corta_por_techo_y_no_se_promueve(monkeypatch):
    """Agotar el techo es un `unknown` HONESTO: jamás proved/refuted."""
    import time

    def _eterno(kind, **kw):
        time.sleep(300)                      # el hijo nunca terminaría solo
        return {"result": "proved", "kind": kind, "detail": "no debería verse"}

    monkeypatch.setattr(ga, "_prove_direct", _eterno)
    t0 = time.time()
    r = ga.prove("int_forall", expr="n >= 0", vars=["n"], timeout_s=3.0,
                 beat_every_s=1.0)
    elapsed = time.time() - t0
    assert r["result"] == "unknown"          # NUNCA se promueve
    assert "timeout" in r["detail"]
    assert elapsed < 30                      # el hijo fue MATADO, no esperado


def test_late_mientras_el_solve_trabaja(monkeypatch):
    """Sin latido, 'demostrando' y 'colgado' se ven idénticos desde el tablero."""
    import time

    def _lento(kind, **kw):
        time.sleep(2.5)
        return {"result": "proved", "kind": kind, "detail": "ok", "backend": "z3"}

    monkeypatch.setattr(ga, "_prove_direct", _lento)
    beats: list[float] = []
    r = ga.prove("int_forall", expr="n*n >= 0", vars=["n"], timeout_s=60.0,
                 beat_every_s=0.5, on_beat=beats.append)
    assert r["result"] == "proved"
    assert len(beats) >= 2                   # latió DURANTE, no solo al final
    assert beats == sorted(beats)            # elapsed monótono creciente


def test_latido_roto_no_tumba_el_solve(monkeypatch):
    """El latido es cosmético: si falla, el veredicto igual llega."""
    import time

    def _lento(kind, **kw):
        time.sleep(1.5)
        return {"result": "proved", "kind": kind, "detail": "ok", "backend": "z3"}

    def _boom(_elapsed):
        raise RuntimeError("tablero caído")

    monkeypatch.setattr(ga, "_prove_direct", _lento)
    r = ga.prove("int_forall", expr="n*n >= 0", vars=["n"], timeout_s=60.0,
                 beat_every_s=0.3, on_beat=_boom)
    assert r["result"] == "proved"


def test_fallo_al_lanzar_hijo_se_loguea_y_queda_marcado_degradado(monkeypatch, caplog):
    """Si `ctx.Process(...)` no puede lanzarse (fork falla), el fallback a
    `_prove_direct` sigue existiendo ("mejor resolver que no resolver") pero ya NO
    puede ser silencioso: debe quedar logueado con traceback y el resultado debe
    decir explícitamente que corrió sin aislamiento ni techo de tiempo, para que esto
    sea diagnosticable sin tener que hurgar en /proc como con la Ronda 4/Ronda 7."""
    import multiprocessing as mp

    class _BoomContext:
        def Queue(self, *a, **kw):
            raise RuntimeError("fork no disponible en este runtime (simulado)")

    monkeypatch.setattr(mp, "get_context", lambda name: _BoomContext())
    caplog.set_level(logging.ERROR, logger="acero.science.proof_assistant")

    r = ga.prove("bool_sat", expr="a", vars=["a"], sort="bool")

    assert r["degraded_no_isolation"] is True
    assert r["result"] == "proved"               # el fallback SÍ resuelve el claim
    assert any("aislamiento" in rec.message or "fork" in rec.message
               for rec in caplog.records)
    assert any(rec.exc_info for rec in caplog.records)   # traceback real, no solo texto


def test_techo_por_defecto_es_de_dias_no_de_minutos(monkeypatch):
    """Merari: "no pongas límite de tiempo al programa". El techo existe para que el
    solve sea observable y matable, no para apurar a Gödel."""
    assert ga._default_timeout_s() >= 86400
    monkeypatch.setenv("ACERO_Z3_TIMEOUT_S", "7200")
    assert ga._default_timeout_s() == 7200.0
    monkeypatch.setenv("ACERO_Z3_TIMEOUT_S", "no-es-un-numero")
    assert ga._default_timeout_s() >= 86400          # basura → vuelve al default
