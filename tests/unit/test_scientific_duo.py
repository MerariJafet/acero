"""Scientific Duo: diálogo científico persistente Director ↔ Claude(Ejecutor).

REDISEÑO 2026-08-15: la v1 invocaba `codex exec` directamente -- el clasificador de
seguridad del entorno lo bloqueó como exfiltración de datos (leer archivos locales y
mandarlos a un servicio externo), bloqueo que la autorización del usuario no puede
saltar. Merari decidió no tocar permisos y en cambio corregir la arquitectura: este
módulo ahora es agnóstico de proveedor (`DirectorBackend`) y nunca hace red ni
subprocess -- por eso estos tests NUNCA necesitan mockear una llamada de red: el
`MockDirector` es simplemente un objeto en memoria, y `FileDirectorBackend` solo lee/
escribe archivos locales (redirigidos a tmp_path, nunca al
research/reto50/scientific_duo/ real)."""
from __future__ import annotations

import json

import pytest

from acero.science import scientific_duo as sd


@pytest.fixture(autouse=True)
def _rutas_aisladas(tmp_path, monkeypatch):
    """Redirige TODAS las rutas de escritura a tmp_path. Nunca debe tocar el
    research/reto50/scientific_duo/ real."""
    monkeypatch.setattr(sd, "DUO_DIR", tmp_path)
    monkeypatch.setattr(sd, "DIALOGUE_PATH", tmp_path / "dialogue.jsonl")
    monkeypatch.setattr(sd, "DECISIONS_PATH", tmp_path / "decisions.jsonl")
    state_path = tmp_path / "scientific_state.json"
    monkeypatch.setattr(sd, "STATE_PATH", state_path)
    state_path.write_text(json.dumps({
        "research_question": "pregunta de prueba",
        "last_director_decision": None,
    }), encoding="utf-8")
    monkeypatch.setattr(sd, "REQUEST_PATH", tmp_path / "director_request.json")
    monkeypatch.setattr(sd, "RESPONSE_PATH", tmp_path / "director_response.json")
    # SCHEMAS_DIR y CONTEXT_SEED_PATH quedan apuntando a los reales (solo lectura)
    yield tmp_path


DIRECTOR_OK = {
    "state_assessment": "el greedy no demuestra exclusividad",
    "accepted_evidence": ["F5"],
    "rejected_interpretations": ["k=107 abre exclusivamente esa puerta"],
    "open_uncertainties": ["si 21 llaves ya cubrian 2e11"],
    "rival_hypotheses": [{"id": "H0", "statement": "es artefacto del greedy",
                          "falsifier": "encontrar un cover de 21 exacto"}],
    "next_experiment": {
        "objective": "resolver C(2e11) con solver iterativo de hitting-set",
        "why_now": "58 variables, no necesita 29GB de RAM",
        "inputs": ["mascaras en formato uint64"],
        "procedure": ["proponer candidato <=21", "buscar contraejemplo", "repetir"],
        "success_condition": "SAT explicito o UNSAT demostrado",
        "failure_condition": "no converge",
        "expected_information_gain": 0.9,
        "estimated_cost": "minutos",
        "resource_limits": {},
    },
    "claims_forbidden": ["C(2e11)=22 sin certificado exacto"],
    "decision": "EXECUTE",
}


# --- schema (sin cambios respecto a la v1 -- sigue siendo agnostico de proveedor) ----
def test_validate_director_response_valido():
    ok, err = sd.validate_director_response(DIRECTOR_OK)
    assert ok
    assert err is None


def test_validate_director_response_invalido_falta_decision():
    malo = dict(DIRECTOR_OK)
    del malo["decision"]
    ok, err = sd.validate_director_response(malo)
    assert not ok
    assert "decision" in err


def test_validate_director_response_decision_fuera_de_enum():
    malo = dict(DIRECTOR_OK)
    malo["decision"] = "RESELLAR_PREMISA"  # el Director NO puede hacer esto
    ok, _ = sd.validate_director_response(malo)
    assert not ok


def test_validate_executor_report_status_valido():
    ok, _ = sd.validate_executor_report({"status": "PLAN_BLOCKED", "reason": "x"})
    assert ok


def test_validate_executor_report_status_invalido():
    ok, _ = sd.validate_executor_report({"status": "INVENTADO"})
    assert not ok


# --- frontera de sanitización (evidencia vs metadata de máquina) --------------------
def test_build_evidence_packet_limpio_pasa():
    packet = sd.build_evidence_packet(
        "¿C(2e11) es 21 o 22?",
        {"G": 22, "keys": 58, "masks_103": [103, 139, 247]},
        ["G=22 pero C<=21", "C=22"],
    )
    assert packet["question"] == "¿C(2e11) es 21 o 22?"
    assert packet["known_evidence"]["G"] == 22


def test_build_evidence_packet_rechaza_ruta_absoluta():
    with pytest.raises(ValueError, match="metadata de máquina"):
        sd.build_evidence_packet("q", {"backup": "/home/merari-acero/x.ckpt"}, [])


def test_build_evidence_packet_rechaza_sha256():
    with pytest.raises(ValueError):
        sd.build_evidence_packet(
            "q", {"hash": "8913547a4f5c4f2c24bab1c80b1c4a39470909313e3138215eb738f10857176c"}, [])


def test_build_evidence_packet_rechaza_ckpt_path():
    with pytest.raises(ValueError):
        sd.build_evidence_packet("q", {"origen": "cover_growth_k500.ckpt"}, [])


def test_build_evidence_packet_rechaza_metadata_anidada():
    with pytest.raises(ValueError):
        sd.build_evidence_packet(
            "q", {"detalle": {"nota": "ver /tmp/algo"}}, [])


# --- MockDirector (backend en memoria, sin red) --------------------------------------
def test_mock_director_submit_y_get_response_inmediato():
    backend = sd.MockDirector(responder=lambda req: DIRECTOR_OK)
    rid = backend.submit({"evidence": {}})
    assert backend.get_response(rid) == DIRECTOR_OK


def test_mock_director_respuesta_asincrona():
    backend = sd.MockDirector()
    rid = backend.submit({"evidence": {}})
    assert backend.get_response(rid) is None  # todavía no responde
    backend.resolve(rid, DIRECTOR_OK)
    assert backend.get_response(rid) == DIRECTOR_OK


# --- FileDirectorBackend (solo archivos locales, sin red ni subprocess) -------------
def test_file_director_backend_escribe_solicitud_sin_red(tmp_path):
    backend = sd.FileDirectorBackend(request_path=tmp_path / "req.json",
                                     response_path=tmp_path / "resp.json")
    rid = backend.submit({"evidence": {"q": "x"}})
    escrito = sd.load_json(tmp_path / "req.json")
    assert escrito["request_id"] == rid
    assert escrito["evidence"] == {"q": "x"}


def test_file_director_backend_sin_respuesta_devuelve_none(tmp_path):
    backend = sd.FileDirectorBackend(request_path=tmp_path / "req.json",
                                     response_path=tmp_path / "resp.json")
    rid = backend.submit({"evidence": {}})
    assert backend.get_response(rid) is None


def test_file_director_backend_lee_respuesta_cuando_aparece(tmp_path):
    backend = sd.FileDirectorBackend(request_path=tmp_path / "req.json",
                                     response_path=tmp_path / "resp.json")
    rid = backend.submit({"evidence": {}})
    # simula al adaptador externo (fuera de este proceso) escribiendo la respuesta
    sd._atomic_write_json(tmp_path / "resp.json", {"request_id": rid, **DIRECTOR_OK})
    resp = backend.get_response(rid)
    assert resp["decision"] == "EXECUTE"


def test_file_director_backend_ignora_respuesta_de_otro_request_id(tmp_path):
    backend = sd.FileDirectorBackend(request_path=tmp_path / "req.json",
                                     response_path=tmp_path / "resp.json")
    rid = backend.submit({"evidence": {}})
    sd._atomic_write_json(tmp_path / "resp.json",
                          {"request_id": "otro-id-distinto", **DIRECTOR_OK})
    assert backend.get_response(rid) is None


# --- anti-bucle ------------------------------------------------------------------------
def test_check_stalled_detecta_objetivo_repetido():
    dialogue = [{"role": "director", "next_action": {"objective": "mismo experimento"}}
                for _ in range(sd.MAX_TURNS_WITHOUT_PROGRESS)]
    assert sd.check_stalled(dialogue) is True


def test_check_stalled_no_dispara_con_pocos_turnos():
    dialogue = [{"role": "director", "next_action": {"objective": "x"}}]
    assert sd.check_stalled(dialogue) is False


def test_check_stalled_no_dispara_si_objetivos_distintos():
    dialogue = [{"role": "director", "next_action": {"objective": f"experimento {i}"}}
                for i in range(sd.MAX_TURNS_WITHOUT_PROGRESS)]
    assert sd.check_stalled(dialogue) is False


# --- ciclo completo submit -> collect (agnóstico de proveedor) ----------------------
def test_submit_y_collect_ciclo_completo_con_mock():
    backend = sd.MockDirector(responder=lambda req: DIRECTOR_OK)
    rid = sd.submit_director_turn(
        backend, "¿C(2e11) es 21 o 22?", {"G": 22, "keys": 58}, ["G=22 pero C<=21"],
        cycle_id="ciclo-1", first_turn=True)
    entry = sd.collect_director_response(backend, rid, cycle_id="ciclo-1")
    assert entry["message_type"] == "decision"
    assert entry["decision"] == "EXECUTE"
    dialogue = sd.read_jsonl(sd.DIALOGUE_PATH)
    assert len(dialogue) == 1


def test_collect_director_response_no_bloquea_si_no_hay_respuesta():
    backend = sd.MockDirector()  # sin responder -- nunca resuelve
    rid = sd.submit_director_turn(
        backend, "q", {"G": 22}, [], cycle_id="ciclo-1", first_turn=True)
    assert sd.collect_director_response(backend, rid, cycle_id="ciclo-1") is None
    assert sd.read_jsonl(sd.DIALOGUE_PATH) == []  # nada que registrar todavia


def test_collect_director_response_json_roto_se_degrada_sin_ejecutar_nada():
    backend = sd.MockDirector(responder=lambda req: "esto no es JSON valido {{{")
    rid = sd.submit_director_turn(backend, "q", {}, [], cycle_id="c1", first_turn=True)
    entry = sd.collect_director_response(backend, rid, cycle_id="c1")
    assert entry["message_type"] == "degraded"
    assert entry["next_action"] is None


def test_collect_director_response_no_valida_schema_se_degrada():
    incompleto = dict(DIRECTOR_OK)
    del incompleto["decision"]
    backend = sd.MockDirector(responder=lambda req: incompleto)
    rid = sd.submit_director_turn(backend, "q", {}, [], cycle_id="c1", first_turn=True)
    entry = sd.collect_director_response(backend, rid, cycle_id="c1")
    assert entry["message_type"] == "degraded"


def test_collect_director_response_actualiza_estado_y_decisiones():
    backend = sd.MockDirector(responder=lambda req: DIRECTOR_OK)
    rid = sd.submit_director_turn(backend, "q", {}, [], cycle_id="c1", first_turn=True)
    sd.collect_director_response(backend, rid, cycle_id="c1")
    state = sd.load_json(sd.STATE_PATH)
    assert state["last_director_decision"] == "EXECUTE"
    decisiones = sd.read_jsonl(sd.DECISIONS_PATH)
    assert len(decisiones) == 1


def test_submit_director_turn_no_toca_red_ni_subprocess(monkeypatch):
    """Si alguien reintroduce una llamada de red/subprocess en el path de submit,
    este test debe fallar."""
    import subprocess
    def _bomba(*a, **k):
        raise AssertionError("submit_director_turn NO debe invocar subprocess")
    monkeypatch.setattr(subprocess, "run", _bomba)
    backend = sd.MockDirector(responder=lambda req: DIRECTOR_OK)
    sd.submit_director_turn(backend, "q", {}, [], cycle_id="c1", first_turn=True)


# --- reportes del ejecutor (sin cambios) --------------------------------------------
def test_record_executor_report_plan_blocked():
    reporte = {
        "status": "PLAN_BLOCKED",
        "reason": "El experimento presupone S21_old pero ese snapshot no existe.",
        "evidence": ["busqueda en workspace"],
        "proposed_substitute": "Solver iterativo de hitting-set sobre las 58 llaves.",
    }
    entry = sd.record_executor_report(reporte, cycle_id="c1", turn=2)
    assert entry["message_type"] == "execution_report"


def test_record_executor_report_invalido_se_registra_no_se_descarta():
    entry = sd.record_executor_report({"status": "NO_EXISTE"}, cycle_id="c1", turn=1)
    assert entry["message_type"] == "invalid_report"
    assert "schema_error" in entry
    assert len(sd.read_jsonl(sd.DIALOGUE_PATH)) == 1


def test_append_jsonl_es_append_only(tmp_path):
    path = tmp_path / "log.jsonl"
    sd.append_jsonl(path, {"n": 1})
    sd.append_jsonl(path, {"n": 2})
    assert sd.read_jsonl(path) == [{"n": 1}, {"n": 2}]


# --- artefactos reales del repo -------------------------------------------------------
def test_los_schemas_reales_son_json_valido_y_cargan():
    director_schema = sd.load_json(sd.SCHEMAS_DIR / "director_response.schema.json")
    executor_schema = sd.load_json(sd.SCHEMAS_DIR / "executor_report.schema.json")
    assert director_schema["title"] == "director_response"
    assert executor_schema["title"] == "executor_report"


def test_context_seed_real_existe_y_menciona_lo_esencial():
    texto = sd.CONTEXT_SEED_PATH.read_text(encoding="utf-8")
    assert "307" in texto
    assert "G(N)" in texto and "C(N)" in texto
