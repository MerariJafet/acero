"""Economic Mode — an advisor for growing and sustaining a HEALTHY economy of the
system's resources, grounded in the researcher's REAL finances from NEXUS.

You dialogue about ideas to generate/farm resources and a spending strategy; the
advisor reasons over the actual NEXUS snapshot (income, expenses by category,
balances) and, crucially, will QUESTION each idea adversarially until it holds up
(viable | needs_work | reject). It never invents figures (if NEXUS has no data it
says so), never executes trades/transfers, and is NOT licensed financial advice —
it plans; the human decides.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.ids import new_id

ECON_TURN_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string"},                # markdown, grounded in snapshot
        "insights": {"type": "array", "items": {"type": "string"}},
        "spend_strategy": {"type": "array", "items": {"type": "string"}},
        "growth_ideas": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "hook": {"type": "string"},
                           "expected_effect": {"type": "string"}},
            "required": ["title", "hook", "expected_effect"],
            "additionalProperties": False}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
        "canvas_svg": {"type": "string"},              # LLM-drawn chart/diagram or ""
        "health": {
            "type": "object",
            "properties": {"score": {"type": "number"}, "reason": {"type": "string"}},
            "required": ["score", "reason"], "additionalProperties": False},
    },
    "required": ["analysis", "insights", "spend_strategy", "growth_ideas",
                 "risks", "questions", "canvas_svg", "health"],
    "additionalProperties": False,
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},                 # viable | needs_work | reject
        "why": {"type": "string"},
        "fixes": {"type": "array", "items": {"type": "string"}},
        "viability_score": {"type": "number"},
    },
    "required": ["verdict", "why", "fixes", "viability_score"],
    "additionalProperties": False,
}

_SYS = (
    "Eres el ASESOR ECONÓMICO de ACERO. Ayudas a Merari a hacer CRECER y sostener "
    "una economía SANA de sus recursos: estrategia de gasto e ideas para generar/"
    "farmear recursos. Razonas SOBRE LOS DATOS REALES del snapshot de NEXUS (ingresos, "
    "gastos por categoría, balances). REGLAS DURAS: NUNCA inventes cifras — si el "
    "snapshot no está disponible, dilo y pide conectar NEXUS o importar datos; NO das "
    "asesoría de inversión personalizada ni ejecutas transacciones; PLANEAS, el humano "
    "decide. Sé concreto y honesto (incluye riesgos).\n"
    "- analysis: lee el snapshot y di qué ves (dónde se va el dinero, ratios, tendencias) "
    "en markdown corto. Cita números SOLO si están en el snapshot.\n"
    "- insights: 2-5 observaciones accionables.\n"
    "- spend_strategy: 2-5 movimientos concretos de estrategia de gasto.\n"
    "- growth_ideas: 2-5 ideas para GENERAR recursos, cada una con hook y expected_effect.\n"
    "- risks: riesgos/supuestos.\n"
    "- questions: preguntas para afinar contigo.\n"
    "- canvas_svg: un gráfico o diagrama en SVG INLINE (viewBox=\"0 0 400 260\", sin "
    "ancho/alto fijos, fondo transparente, texto fill #e6edf3, barras/trazos #8ab4f8, "
    "cajas #1c2333, etiquetas en español, NADA de <script>) que visualice el gasto o el "
    "plan; cadena vacía si no aplica.\n"
    "- health: score 0..1 de salud financiera (0=crítico,1=excelente) con reason. Si no "
    "hay datos, score bajo y reason='sin datos de NEXUS'."
)

_CRIT_SYS = (
    "Eres un ASESOR ADVERSARIAL de ACERO. Cuestiona esta idea económica HASTA que "
    "funcione o se caiga: evalúa viabilidad real contra el snapshot de NEXUS (costo, "
    "flujo de caja, esfuerzo, retorno esperado, riesgos, supuestos frágiles). Sé "
    "escéptico y honesto. verdict='viable' solo si de verdad se sostiene con los datos; "
    "'needs_work' si es prometedora pero falta; 'reject' si no cuadra. Da 'fixes' "
    "concretos y viability_score 0..1. No inventes cifras."
)


# --- session storage ----------------------------------------------------------

def econ_root() -> Path:
    env = os.environ.get("ACERO_ECON_ROOT", "").strip()
    return Path(env) if env else repo_root() / "acero_data" / "economics"


def _sdir(sid: str) -> Path:
    d = econ_root() / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(sid: str) -> dict[str, Any]:
    f = _sdir(sid) / "session.json"
    if not f.exists():
        raise KeyError(f"economic session {sid} not found")
    return json.loads(f.read_text(encoding="utf-8"))


def _save(sid: str, data: dict[str, Any]) -> None:
    (_sdir(sid) / "session.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append(sid: str, fname: str, rec: dict[str, Any]) -> None:
    with (_sdir(sid) / fname).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read_jsonl(sid: str, fname: str) -> list[dict[str, Any]]:
    f = _sdir(sid) / fname
    if not f.exists():
        return []
    out = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            continue
    return out


def list_sessions() -> list[dict[str, Any]]:
    root = econ_root()
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(root.iterdir()):
        f = d / "session.json"
        if not d.is_dir() or not d.name.startswith("esess") or not f.exists():
            continue
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        out.append({"session_id": s.get("id", d.name), "goal": s.get("goal", ""),
                    "created_at": s.get("created_at", "")})
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


def _snap_summary(s: dict[str, Any]) -> str:
    if not s or not s.get("available"):
        return "SIN DATOS de NEXUS (no inventes cifras; sugiere conectar/importar)."
    cats = ", ".join(f"{c['category']}={c['amount']}" for c in s.get("expenses_by_category", [])[:8])
    return (f"moneda={s.get('currency')}, ingresos={s.get('income')}, "
            f"gastos={s.get('expenses')}, neto={s.get('net')}; "
            f"gasto por categoría: {cats or '—'}; "
            f"cuentas: {', '.join(f'{a['name']}={a['balance']}' for a in s.get('accounts', [])[:6]) or '—'}")


class EconomicAdvisor:
    """Structured advisor turn + adversarial idea critique. Provider injectable."""

    def __init__(self, provider: Any = None) -> None:
        self._provider = provider

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider(timeout_sec=220)

    def turn(self, snapshot: dict[str, Any], goal: str, message: str) -> dict[str, Any]:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return self._fallback()
        prompt = (f"{_SYS}\n\nSNAPSHOT NEXUS: {_snap_summary(snapshot)}\n"
                  f"META DEL USUARIO: {goal or '(sin meta explícita)'}\n"
                  f"MENSAJE: {message}\n\nDevuelve el turno.")
        try:
            out = prov.complete_json(prompt, ECON_TURN_SCHEMA, temperature=0.4)
            return self._normalize(out) if isinstance(out, dict) else self._fallback()
        except Exception:  # noqa: BLE001
            return self._fallback()

    def critique(self, snapshot: dict[str, Any], idea: str) -> dict[str, Any]:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return {"verdict": "needs_work", "why": "sin IA disponible",
                    "fixes": [], "viability_score": 0.0}
        prompt = (f"{_CRIT_SYS}\n\nSNAPSHOT NEXUS: {_snap_summary(snapshot)}\n"
                  f"IDEA A CUESTIONAR: {idea}\n\nDevuelve el veredicto.")
        try:
            out = prov.complete_json(prompt, CRITIQUE_SCHEMA, temperature=0.3)
            v = str(out.get("verdict") or "needs_work").lower()
            return {"verdict": v if v in {"viable", "needs_work", "reject"} else "needs_work",
                    "why": str(out.get("why") or "")[:500],
                    "fixes": [str(x)[:200] for x in (out.get("fixes") or [])[:6]],
                    "viability_score": float(out.get("viability_score") or 0.0)}
        except Exception:  # noqa: BLE001
            return {"verdict": "needs_work", "why": "no evaluable", "fixes": [],
                    "viability_score": 0.0}

    @staticmethod
    def _normalize(out: dict[str, Any]) -> dict[str, Any]:
        for k in ("insights", "spend_strategy", "growth_ideas", "risks", "questions"):
            out.setdefault(k, [])
        out.setdefault("analysis", "")
        out.setdefault("canvas_svg", "")
        h = out.get("health") or {}
        out["health"] = {"score": float(h.get("score") or 0.0),
                         "reason": str(h.get("reason") or "")[:300]}
        out["growth_ideas"] = (out.get("growth_ideas") or [])[:6]
        return out

    @staticmethod
    def _fallback() -> dict[str, Any]:
        return {"analysis": "(asesor sin IA disponible)", "insights": [],
                "spend_strategy": [], "growth_ideas": [], "risks": [], "questions": [],
                "canvas_svg": "", "health": {"score": 0.0, "reason": "sin IA"}}


class EconomicEngine:
    def __init__(self, advisor: EconomicAdvisor | None = None, connector: Any = None) -> None:
        self._advisor = advisor or EconomicAdvisor()
        self._connector = connector

    def snapshot(self) -> dict[str, Any]:
        if self._connector is not None:
            return self._connector.fetch_snapshot()
        from ..integrations.nexus import NexusConnector
        return NexusConnector().fetch_snapshot()

    def start(self, goal: str) -> dict[str, Any]:
        sid = new_id("esess")
        snap = self.snapshot()
        sess = {"id": sid, "goal": goal[:300], "created_at": now_iso(),
                "snapshot": snap}
        _save(sid, sess)
        turn = self._advisor.turn(snap, goal, f"Analiza mi economía y mi meta: {goal}")
        _append(sid, "messages.jsonl", {"role": "assistant", "turn": turn, "ts": now_iso()})
        return {"session_id": sid, "snapshot": snap, "turn": turn}

    def ask(self, sid: str, message: str) -> dict[str, Any]:
        sess = _load(sid)
        _append(sid, "messages.jsonl", {"role": "user", "text": message, "ts": now_iso()})
        turn = self._advisor.turn(sess.get("snapshot") or {}, sess.get("goal", ""), message)
        _append(sid, "messages.jsonl", {"role": "assistant", "turn": turn, "ts": now_iso()})
        return {"turn": turn}

    def critique(self, sid: str, idea: str) -> dict[str, Any]:
        sess = _load(sid)
        verdict = self._advisor.critique(sess.get("snapshot") or {}, idea)
        _append(sid, "critiques.jsonl", {"idea": idea[:400], "verdict": verdict,
                                         "ts": now_iso()})
        return {"verdict": verdict}

    def promote(self, sid: str, idea: str) -> dict[str, Any]:
        _load(sid)                                    # validates the session exists
        rec = {"id": new_id("eproj"), "idea": idea[:400], "created_at": now_iso(),
               "status": "ACTIVE"}
        _append(sid, "projects.jsonl", rec)
        return {"ok": True, "project": rec}

    def get(self, sid: str) -> dict[str, Any]:
        sess = _load(sid)
        return {"session": sess, "messages": _read_jsonl(sid, "messages.jsonl"),
                "critiques": _read_jsonl(sid, "critiques.jsonl"),
                "projects": _read_jsonl(sid, "projects.jsonl")}
