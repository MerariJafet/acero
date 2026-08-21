"""Scientific Duo — diálogo científico persistente Director ↔ Claude(Ejecutor).

REDISEÑO 2026-08-15: la primera versión hacía que Claude invocara `codex exec`
directamente (subprocess) mandándole contexto de investigación real. El clasificador de
seguridad del entorno lo bloqueó como exfiltración de datos -- correctamente: desde
dentro de este proceso, "leer archivos locales y mandarlos a un servicio externo" es
exactamente ese patrón, sin importar la autorización del usuario. Merari decidió NO
tocar permisos y en cambio corregir la arquitectura: **Claude nunca transfiere datos a
un proveedor externo**. Este módulo es ahora agnóstico de proveedor:

- `DirectorBackend` es la interfaz (`submit`/`get_response`). No sabe ni le importa si
  el Director es Codex, otro modelo, un humano o un ensemble.
- `FileDirectorBackend` escribe la solicitud a un archivo local
  (`director_request.json`) y lee la respuesta de otro (`director_response.json`).
  Sin red, sin subprocess, sin API. Un proceso FUERA de este entorno (administrado por
  Merari) es quien de verdad decide cómo (o si) contactar a un LLM externo -- ese
  adaptador queda explícitamente fuera de este módulo y no debe implementarse aquí.
- `MockDirector` es un backend en memoria, solo para tests.
- `build_evidence_packet` separa EVIDENCIA (hechos matemáticos, incertidumbres,
  hipótesis) de METADATA DE MÁQUINA (rutas absolutas, PIDs, hashes de disco, usuarios,
  paths de checkpoints) -- lo segundo nunca sale de este módulo hacia una solicitud.

El Director NUNCA ejecuta cambios ni resella la premisa -- eso sigue siendo
`portal/premise.py` + decisión humana. Su respuesta se valida contra JSON Schema antes
de aceptarla; si no valida, se pide una corrección, y si vuelve a fallar se registra
como degradación sin ejecutar ningún plan ambiguo.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

import jsonschema

from ..core.workspace import data_path

DUO_DIR = data_path(
    "investigaciones/erdos-straus/scientific_duo",
    legacy=Path(__file__).resolve().parents[3] / "research" / "reto50"
    / "scientific_duo",
)
SCHEMAS_DIR = DUO_DIR / "schemas"
DIALOGUE_PATH = DUO_DIR / "dialogue.jsonl"
DECISIONS_PATH = DUO_DIR / "decisions.jsonl"
STATE_PATH = DUO_DIR / "scientific_state.json"
HYPOTHESES_PATH = DUO_DIR / "hypotheses.json"
CONTEXT_SEED_PATH = DUO_DIR / "context_seed.md"
REQUEST_PATH = DUO_DIR / "director_request.json"
RESPONSE_PATH = DUO_DIR / "director_response.json"

MAX_TURNS_WITHOUT_PROGRESS = 5  # ping-pong -> STALLED


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Mismo patrón que `cover_growth.py::_atomic_write`: nunca dejar un archivo de
    estado a medio escribir si el proceso muere a mitad de camino."""
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def append_jsonl(path: Path, entry: dict) -> None:
    """Append-only. Nunca reescribe historia -- ni siquiera para corregir un entry
    malo: si algo salió mal, se registra un entry NUEVO que lo señala."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# --- validación de esquema ------------------------------------------------------------
def validate_director_response(obj: dict) -> tuple[bool, str | None]:
    schema = load_json(SCHEMAS_DIR / "director_response.schema.json")
    try:
        jsonschema.validate(obj, schema)
        return True, None
    except jsonschema.ValidationError as exc:
        return False, str(exc.message)


def validate_executor_report(obj: dict) -> tuple[bool, str | None]:
    schema = load_json(SCHEMAS_DIR / "executor_report.schema.json")
    try:
        jsonschema.validate(obj, schema)
        return True, None
    except jsonschema.ValidationError as exc:
        return False, str(exc.message)


# --- frontera de sanitización: evidencia vs metadata de máquina -----------------------
def build_evidence_packet(question: str, known_evidence: dict,
                           open_interpretations: list[str]) -> dict:
    """Construye lo único que puede salir hacia un Director externo: pregunta,
    hechos matemáticos, e interpretaciones abiertas. Rechaza explícitamente cualquier
    valor que huela a metadata de máquina (rutas absolutas, hashes largos, 'pid',
    nombres de usuario) -- si algo así se cuela en `known_evidence`, es un bug de quien
    llama a esta función, no algo que este módulo deba pasar silenciosamente."""
    _reject_machine_metadata(known_evidence)
    return {
        "question": question,
        "known_evidence": known_evidence,
        "open_interpretations": list(open_interpretations),
    }


_METADATA_MARKERS = ("/home/", "/tmp/", "/research/", "pid", "PID", ".ckpt", ".json",
                     "sha256", "usuario", "username")


def _reject_machine_metadata(obj: Any, *, path: str = "known_evidence") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_machine_metadata(v, path=f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_machine_metadata(v, path=f"{path}[{i}]")
    elif isinstance(obj, str):
        low = obj.lower()
        for marker in _METADATA_MARKERS:
            if marker.lower() in low:
                raise ValueError(
                    f"{path} contiene algo que parece metadata de máquina "
                    f"('{marker}') -- el Director recibe hechos matemáticos, no "
                    f"rutas/hashes/PIDs. Valor: {obj!r}")
        if len(obj) == 64 and all(c in "0123456789abcdef" for c in low):
            raise ValueError(f"{path} parece un hash sha256 crudo: {obj!r}")


# --- backend del Director (agnóstico de proveedor) -------------------------------------
class DirectorBackend(Protocol):
    """Interfaz que cualquier Director debe cumplir. Este módulo NUNCA sabe si el
    backend real es Codex, otro modelo, un humano o un ensemble -- y no debe saberlo."""

    def submit(self, request: dict) -> str:
        """Encola una solicitud, devuelve un id para recuperarla después."""
        ...

    def get_response(self, request_id: str) -> dict | None:
        """None si la respuesta todavía no está lista -- nunca bloquea."""
        ...


class MockDirector:
    """Backend en memoria, solo para tests. Puede precargarse con una respuesta fija
    o una función que decide la respuesta a partir de la solicitud."""

    def __init__(self, responder=None):
        self._responder = responder
        self._pending: dict[str, dict] = {}
        self._ready: dict[str, dict] = {}

    def submit(self, request: dict) -> str:
        request_id = str(uuid.uuid4())
        self._pending[request_id] = request
        if self._responder is not None:
            self._ready[request_id] = self._responder(request)
        return request_id

    def get_response(self, request_id: str) -> dict | None:
        return self._ready.get(request_id)

    def resolve(self, request_id: str, response: dict) -> None:
        """Para tests que quieren simular una respuesta que llega DESPUÉS del submit
        (asincronía real, no inmediata)."""
        self._ready[request_id] = response


class FileDirectorBackend:
    """Sin red, sin subprocess, sin API. Escribe la solicitud a un archivo local y
    lee la respuesta de otro. Un proceso administrado por Merari, FUERA de este
    entorno, es responsable de leer `request_path`, decidir qué hacer con ella
    (incluyendo, si así lo decide, contactar a un LLM externo) y escribir
    `response_path`. Ese adaptador NO vive en este repo ni se ejecuta desde aquí."""

    def __init__(self, request_path: Path = REQUEST_PATH,
                 response_path: Path = RESPONSE_PATH):
        self.request_path = request_path
        self.response_path = response_path

    def submit(self, request: dict) -> str:
        request_id = str(uuid.uuid4())
        payload = {"request_id": request_id, "submitted_at": _now_iso(), **request}
        _atomic_write_json(self.request_path, payload)
        return request_id

    def get_response(self, request_id: str) -> dict | None:
        if not self.response_path.exists():
            return None
        try:
            resp = load_json(self.response_path)
        except (json.JSONDecodeError, OSError):
            return None
        if resp.get("request_id") != request_id:
            return None
        return resp


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S")


# --- anti-bucle -------------------------------------------------------------------------
def check_stalled(dialogue_entries: list[dict], window: int = MAX_TURNS_WITHOUT_PROGRESS
                   ) -> bool:
    """STALLED si, en la ventana de los últimos `window` turnos del Director, el
    objetivo del siguiente experimento propuesto se repite literalmente."""
    director_turns = [e for e in dialogue_entries if e.get("role") == "director"]
    recent = director_turns[-window:]
    if len(recent) < window:
        return False
    objectives = [(e.get("next_action") or {}).get("objective") for e in recent]
    return len(set(objectives)) <= 1 and objectives[0] is not None


# --- ciclo del Director (agnóstico de proveedor) ----------------------------------------
def _parse_response_json(raw: dict | str) -> dict | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def submit_director_turn(backend: DirectorBackend, question: str, known_evidence: dict,
                          open_interpretations: list[str], *, cycle_id: str,
                          first_turn: bool = False) -> str:
    """Construye la solicitud (con el paquete de evidencia sanitizado, y el
    context_seed solo la primera vez de un ciclo) y la manda al backend. Devuelve un
    request_id para recuperar la respuesta después con `collect_director_response`."""
    packet = build_evidence_packet(question, known_evidence, open_interpretations)
    request = {
        "cycle_id": cycle_id,
        "schema": "director_response.schema.json",
        "context_seed": CONTEXT_SEED_PATH.read_text(encoding="utf-8") if first_turn else None,
        "evidence": packet,
        "instructions": (
            "Eres el Director Científico. Responde con un objeto JSON que cumpla el "
            "schema director_response. Sé crítico: qué se demostró realmente, qué "
            "interpretación no se sigue de los datos, si hay una explicación más "
            "simple, qué experimento separa mejor los rivales. No propongas resellar "
            "la premisa. Nunca declares Erdős-Straus resuelto."
        ),
    }
    return backend.submit(request)


def collect_director_response(backend: DirectorBackend, request_id: str, *,
                               cycle_id: str) -> dict | None:
    """None si el Director todavía no respondió -- nunca bloquea ni reintenta por su
    cuenta. Cuando hay respuesta, valida contra el schema (un reintento vía
    `retry_director_turn` si falla) y deja constancia en dialogue.jsonl."""
    raw = backend.get_response(request_id)
    if raw is None:
        return None

    dialogue = read_jsonl(DIALOGUE_PATH)
    turn = len(dialogue) + 1
    parsed = _parse_response_json(raw)

    entry = {
        "timestamp": _now_iso(),
        "research_cycle_id": cycle_id,
        "turn": turn,
        "agent": "director",
        "role": "director",
        "message_type": "decision",
    }
    if parsed is None:
        entry["message_type"] = "degraded"
        entry["summary"] = "Respuesta del Director no es JSON parseable"
        entry["next_action"] = None
        entry["confidence"] = 0.0
        append_jsonl(DIALOGUE_PATH, entry)
        return entry

    ok, err = validate_director_response(parsed)
    if not ok:
        entry["message_type"] = "degraded"
        entry["summary"] = f"Respuesta del Director no valida contra schema: {err}"
        entry["next_action"] = None
        entry["confidence"] = 0.0
        append_jsonl(DIALOGUE_PATH, entry)
        return entry

    entry["summary"] = parsed["state_assessment"]
    entry["claims"] = parsed.get("accepted_evidence", [])
    entry["criticisms"] = parsed.get("rejected_interpretations", [])
    entry["next_action"] = parsed.get("next_experiment")
    entry["decision"] = parsed.get("decision")
    entry["rival_hypotheses"] = parsed.get("rival_hypotheses", [])
    nxt = parsed.get("next_experiment") or {}
    entry["confidence"] = nxt.get("expected_information_gain", 0.0)
    append_jsonl(DIALOGUE_PATH, entry)

    append_jsonl(DECISIONS_PATH, {
        "timestamp": entry["timestamp"], "cycle_id": cycle_id, "turn": turn,
        "decision": entry["decision"], "next_experiment": entry.get("next_action"),
    })
    state = load_json(STATE_PATH)
    state["last_director_decision"] = entry["decision"]
    _atomic_write_json(STATE_PATH, state)

    if check_stalled(read_jsonl(DIALOGUE_PATH)):
        append_jsonl(DIALOGUE_PATH, {
            "timestamp": _now_iso(), "research_cycle_id": cycle_id, "turn": turn + 1,
            "agent": "system", "role": "system", "message_type": "STALLED",
            "summary": "Mismo objetivo repetido sin evidencia nueva en "
                       f"{MAX_TURNS_WITHOUT_PROGRESS} turnos -- forzar representación "
                       "nueva, rival explícito, o cierre parcial.",
        })
    return entry


def record_executor_report(report: dict, *, cycle_id: str, turn: int) -> dict:
    """Claude registra su reporte. Valida contra el schema del ejecutor antes de
    aceptarlo; un reporte inválido se registra igual (append-only), marcado."""
    ok, err = validate_executor_report(report)
    entry = {
        "timestamp": _now_iso(),
        "research_cycle_id": cycle_id,
        "turn": turn,
        "agent": "claude_executor",
        "role": "executor",
        "message_type": "execution_report" if ok else "invalid_report",
    }
    entry.update(report)
    if not ok:
        entry["schema_error"] = err
    append_jsonl(DIALOGUE_PATH, entry)
    return entry
