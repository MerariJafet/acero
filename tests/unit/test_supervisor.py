"""El Auditor: el programa se supervisa a sí mismo. Cada regla nació de un fallo
REAL observado en vivo, así que cada una tiene su prueba. Todo offline: sin LLM,
sin misiones reales — los hechos se inyectan."""

from __future__ import annotations

from acero.portal.supervisor import (
    SEV_BUG,
    SEV_DRIFT,
    SEV_STALL,
    Finding,
    _deterministic_judgement,
    _judge,
    findings_for,
    run_supervision,
)


def _sig(**over):
    """Señales de un proyecto SANO; los tests solo alteran lo que prueban."""
    base = {
        "hipotesis": {"APPROVED": 4, "PROPOSED": 6, "REJECTED": 20},
        "misiones": {"DONE": 5, "RUNNING": 1},
        "n_experimentos": 12, "n_veredictos": 7,
        "ultimo_veredicto_h": 0.2,
        "zombies": [], "estancadas": [],
        "loop": {"status": "running", "paused": False, "ticks": 30,
                 "dry_streak": 0, "ultimo_tick_h": 0.1},
        "decisiones_recientes": ["run_existing", "generate_and_run",
                                 "run_existing", "deepen", "run_existing"],
        "bloqueos_recientes": 1, "lanzadas_recientes": 3,
    }
    base.update(over)
    return base


def _codes(sig, **kw):
    return {f.code for f in findings_for("p1", "Proyecto", sig, **kw)}


def test_proyecto_sano_no_inventa_hallazgos():
    """La regla más importante: sin señales, NO hay problema que reportar."""
    assert _codes(_sig()) == set()


def test_detecta_misiones_zombis():
    """El bug del 2026-08-21: 4 misiones RUNNING sin worker durante 8 horas."""
    f = findings_for("p1", "P", _sig(zombies=[{"id": "msn_x", "hb_age_s": 29000}]))
    z = next(x for x in f if x.code == "MISIONES_ZOMBIS")
    assert z.severity == SEV_BUG and "29000" in z.fact


def test_detecta_centinela_mudo():
    """Dice 'running' pero su hilo murió: el estado miente."""
    sig = _sig(loop={"status": "running", "paused": False, "ticks": 4,
                     "dry_streak": 0, "ultimo_tick_h": 8.0})
    f = findings_for("p1", "P", sig, interval_min=15)
    m = next(x for x in f if x.code == "CENTINELA_MUDO")
    assert m.severity == SEV_BUG


def test_centinela_pausado_o_reciente_no_alarma():
    reciente = _sig(loop={"status": "running", "paused": False, "ticks": 9,
                          "dry_streak": 0, "ultimo_tick_h": 0.2})
    assert "CENTINELA_MUDO" not in _codes(reciente, interval_min=15)


def test_detecta_giro_en_vacio():
    sig = _sig(loop={"status": "running", "paused": False, "ticks": 20,
                     "dry_streak": 4, "ultimo_tick_h": 0.1})
    f = findings_for("p1", "P", sig)
    g = next(x for x in f if x.code == "GIRO_EN_VACIO")
    assert g.severity == SEV_STALL


def test_detecta_actividad_sin_veredictos():
    """El síntoma exacto que Merari vio a ojo: 'no veo que avance nada'."""
    sig = _sig(misiones={"RUNNING": 4, "PENDING": 2}, ultimo_veredicto_h=9.0)
    f = findings_for("p1", "P", sig)
    v = next(x for x in f if x.code == "SIN_VEREDICTOS")
    assert v.severity == SEV_STALL and "9.0" in v.fact


def test_sin_veredictos_nunca_registrado_tambien_alarma():
    sig = _sig(misiones={"RUNNING": 2}, ultimo_veredicto_h=None, n_veredictos=0)
    assert "SIN_VEREDICTOS" in _codes(sig)


def test_misiones_activas_con_veredicto_fresco_no_alarma():
    assert "SIN_VEREDICTOS" not in _codes(
        _sig(misiones={"RUNNING": 3}, ultimo_veredicto_h=0.3))


def test_detecta_bucle_de_decision():
    sig = _sig(decisiones_recientes=["run_existing"] * 5)
    f = findings_for("p1", "P", sig)
    b = next(x for x in f if x.code == "BUCLE_DE_DECISION")
    assert b.severity == SEV_DRIFT


def test_decisiones_variadas_no_son_bucle():
    assert "BUCLE_DE_DECISION" not in _codes(_sig())


def test_detecta_todo_bloqueado_por_eva():
    sig = _sig(bloqueos_recientes=6, lanzadas_recientes=0)
    f = findings_for("p1", "P", sig)
    t = next(x for x in f if x.code == "TODO_BLOQUEADO")
    assert t.severity == SEV_DRIFT
    # la compuerta es soberana: la recomendación culpa al foco, no al gate
    assert "compuerta" in t.recommendation.lower()


def test_detecta_backlog_inflado(monkeypatch):
    """El problema de las 77/104 propuestas sin dictaminar."""
    monkeypatch.setenv("ACERO_PI_MAX_PROPOSED", "15")
    sig = _sig(hipotesis={"APPROVED": 3, "PROPOSED": 90})
    f = findings_for("p1", "P", sig)
    b = next(x for x in f if x.code == "BACKLOG_INFLADO")
    assert b.severity == SEV_STALL and "90" in b.fact


def test_detecta_fallos_en_cascada():
    sig = _sig(misiones={"FAILED": 7, "DONE": 1})
    f = findings_for("p1", "P", sig)
    c = next(x for x in f if x.code == "FALLOS_EN_CASCADA")
    assert c.severity == SEV_BUG


def test_detecta_misiones_pegadas():
    sig = _sig(estancadas=[{"id": "msn_a", "pct": 24, "edad_h": 5.0}])
    assert "MISIONES_PEGADAS" in _codes(sig)


# --- juicio -------------------------------------------------------------------

def test_juicio_sin_hallazgos_es_sano_y_no_inventa_trabajo():
    j = _deterministic_judgement([])
    assert j["salud"] == "sano" and j["prioridad"] == []


def test_juicio_prioriza_bugs_sobre_lo_demas():
    fs = [Finding("GIRO_EN_VACIO", SEV_STALL, "p", "P", "f", "r"),
          Finding("MISIONES_ZOMBIS", SEV_BUG, "p", "P", "f", "r")]
    j = _deterministic_judgement(fs)
    assert j["salud"] == "grave" and j["prioridad"][0] == "MISIONES_ZOMBIS"


def test_juicio_cae_a_deterministico_si_no_hay_llm():
    class _Down:
        def available(self):
            return False
    j = _judge([Finding("X", SEV_STALL, "p", "P", "f", "r")], _Down())
    assert j["via"] == "determinístico"


def test_juicio_usa_el_llm_cuando_esta_disponible():
    class _Bohr:
        def available(self):
            return True

        def complete_json(self, prompt, schema, *, temperature=0.0):
            assert "HALLAZGOS" in prompt          # ve los hechos, no un resumen
            return {"diagnostico": "el gate rechaza todo", "salud": "atención",
                    "prioridad": ["TODO_BLOQUEADO"], "redirigir": "otro ángulo"}
    j = _judge([Finding("TODO_BLOQUEADO", SEV_DRIFT, "p", "P", "f", "r")], _Bohr())
    assert j["via"] == "bohr_llm" and j["redirigir"] == "otro ángulo"


# --- driver -------------------------------------------------------------------

def test_run_supervision_se_apaga_solo_al_cumplir_el_plazo(monkeypatch):
    """Se auto-expira por diseño: una auditoría eterna es ruido que nadie lee."""
    import acero.portal.supervisor as sup
    calls = {"n": 0}

    def _fake_once(**kw):
        calls["n"] += 1
        return {"id": f"sup_{calls['n']}", "ts": "t", "n_hallazgos": 0,
                "juicio": {"salud": "sano"}}

    t = {"now": 0.0}
    monkeypatch.setattr(sup, "supervise_once", _fake_once)
    out = run_supervision(hours=1.0, every_min=15,
                          sleeper=lambda s: t.__setitem__("now", t["now"] + s),
                          clock=lambda: t["now"])
    # 1 h con pasadas cada 15 min: corre y se detiene ANTES de pasarse del plazo
    assert out["passes"] == 4 and calls["n"] == 4
    assert all(r["salud"] == "sano" for r in out["reports"])


def test_run_supervision_respeta_max_passes(monkeypatch):
    import acero.portal.supervisor as sup
    monkeypatch.setattr(sup, "supervise_once", lambda **kw: {
        "id": "s", "ts": "t", "n_hallazgos": 0, "juicio": {"salud": "sano"}})
    out = run_supervision(hours=8.0, every_min=15, max_passes=2,
                          sleeper=lambda s: None, clock=lambda: 0.0)
    assert out["passes"] == 2
