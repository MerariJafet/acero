"""El Auditor — el programa se supervisa a SÍ MISMO (fine-tuning autónomo).

Cada pasada mira el estado REAL de todas las investigaciones vivas y contesta
tres preguntas que hasta ahora solo contestaba un humano leyendo el dashboard:

  1. ¿Esto AVANZA de verdad, o solo se mueve? (actividad ≠ progreso: generar
     hipótesis es barato, producir veredictos es lo que cuenta)
  2. ¿Hay un BUG operando en silencio? (misiones zombis, Centinela muerto,
     fallos en cascada — todo lo que ya nos mordió una vez)
  3. ¿Hay que REDIRIGIR? (bucles de decisión idéntica, backlog inflado, todo
     bloqueado por EVA — el programa trabaja pero apunta al lugar equivocado)

División de poderes, honesta:
  * Los HALLAZGOS son mecánicos: salen de contar cosas del ledger, no de una
    opinión. Un hallazgo se puede verificar mirando los mismos números.
  * El JUICIO (¿qué significa, qué hacer?) lo da Bohr si hay LLM disponible;
    si no, hay un dictamen determinístico. Nunca infla: "sin señales" es un
    resultado legítimo y frecuente.
  * Las CORRECCIONES automáticas son solo las SEGURAS e idempotentes (llamar
    al watchdog de misiones). El programa NO reescribe su propio código: los
    bugs de código se reportan para que un humano (o su agente) los arregle.

Se corre desde cron: `acero supervise --hours 8 --every-min 15`.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id

# --- umbrales (todos configurables por entorno: son juicios, no verdades) ------
STALE_TICK_FACTOR = float(os.environ.get("ACERO_SUP_STALE_TICK_FACTOR", "3.0"))
NO_VERDICT_HOURS = float(os.environ.get("ACERO_SUP_NO_VERDICT_HOURS", "2.0"))
DRY_STREAK_ALERT = int(os.environ.get("ACERO_SUP_DRY_STREAK", "3"))
BACKLOG_FACTOR = float(os.environ.get("ACERO_SUP_BACKLOG_FACTOR", "1.5"))
REPEAT_DECISION_ALERT = int(os.environ.get("ACERO_SUP_REPEAT_DECISION", "5"))
STUCK_MISSION_HOURS = float(os.environ.get("ACERO_SUP_STUCK_MISSION_HOURS", "1.5"))

SEV_BUG = "bug"                 # algo está roto: no funciona como fue diseñado
SEV_STALL = "estancamiento"     # funciona pero no produce conocimiento
SEV_DRIFT = "deriva"            # produce, pero apuntando al lugar equivocado
SEV_OK = "ok"

_TERMINAL = {"DONE", "FAILED"}


@dataclass
class Finding:
    """Un hallazgo VERIFICABLE: el hecho se puede recontar desde el ledger."""
    code: str
    severity: str
    project_id: str
    project_title: str
    fact: str                    # qué se contó (número duro, sin opinión)
    recommendation: str          # qué haría un director con eso
    evidence: dict[str, Any] = field(default_factory=dict)


def _age_h(iso_ts: str | None) -> float | None:
    """Horas desde un timestamp ISO; None si no hay o no parsea."""
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        return None


def project_signals(store: Any, pid: str, *, loop_state: dict[str, Any],
                    feedback: list[dict[str, Any]]) -> dict[str, Any]:
    """Los HECHOS de un proyecto: puro conteo sobre el ledger, cero opinión."""
    def _objs(kind: str) -> list[dict[str, Any]]:
        try:
            return [o for o in store.list_objects(pid, kind=kind) if o.get("id")]
        except Exception:  # noqa: BLE001
            return []

    hyps = _objs("candidate")
    missions = _objs("mission")
    exps = _objs("experiment")
    by_hyp: dict[str, int] = {}
    for h in hyps:
        by_hyp[(h.get("status") or "?").upper()] = by_hyp.get(
            (h.get("status") or "?").upper(), 0) + 1
    by_msn: dict[str, int] = {}
    for m in missions:
        by_msn[(m.get("status") or "?").upper()] = by_msn.get(
            (m.get("status") or "?").upper(), 0) + 1

    now = time.time()
    zombies, stuck = [], []
    for m in missions:
        if (m.get("status") or "").upper() != "RUNNING":
            continue
        hb_age = now - float(m.get("heartbeat_ts") or 0)
        if hb_age > 600:                      # 10 min sin latir: nadie lo está corriendo
            zombies.append({"id": m["id"], "hb_age_s": round(hb_age)})
        started_h = _age_h(m.get("created_at"))
        if started_h and started_h > STUCK_MISSION_HOURS and \
                int(m.get("progress_pct") or 0) < 30:
            stuck.append({"id": m["id"], "pct": m.get("progress_pct"),
                          "edad_h": round(started_h, 1)})

    # averías de la fábrica: ¿los experimentos no corren por límite o por caída?
    # Se clasifica por el TEXTO del error, no solo por la marca 'infra': así el
    # auditor también entiende los registros escritos antes de que esa marca
    # existiera (los 251 del 2026-08-21, precisamente los que había que ver).
    from .experiment_factory import is_infra_failure
    infra_fail, plan_only = 0, 0
    for e in exps:
        fe = e.get("factory_error") or {}
        if fe:
            plan_only += 1
            if fe.get("infra") or is_infra_failure(str(fe.get("error") or "")):
                infra_fail += 1

    # veredictos: LO QUE DE VERDAD CUENTA COMO PROGRESO
    verdicts = [e for e in exps
                if ((e.get("result") or {}).get("verdict")
                    or e.get("verdict"))]
    last_verdict_h = None
    for e in sorted(verdicts, key=lambda x: str(x.get("created_at") or ""),
                    reverse=True)[:1]:
        last_verdict_h = _age_h(e.get("created_at"))

    # decisiones del Centinela: ¿variedad o bucle?
    decisions = [str((r.get("decision") or {}).get("action") or "")
                 for r in feedback][-REPEAT_DECISION_ALERT:]
    blocks_recent = sum(len((r.get("applied") or {}).get("blocks") or [])
                        for r in feedback[-5:])
    started_recent = sum(int((r.get("applied") or {}).get("started") or 0)
                         for r in feedback[-5:])

    return {
        "hipotesis": by_hyp, "misiones": by_msn,
        "n_experimentos": len(exps), "n_veredictos": len(verdicts),
        "ultimo_veredicto_h": last_verdict_h,
        "fabrica_infra_caida": infra_fail, "fabrica_no_ejecutados": plan_only,
        "zombies": zombies, "estancadas": stuck,
        "loop": {"status": loop_state.get("status"),
                 "paused": bool(loop_state.get("paused")),
                 "ticks": int(loop_state.get("ticks") or 0),
                 "dry_streak": int(loop_state.get("dry_streak") or 0),
                 "ultimo_tick_h": _age_h(loop_state.get("last_tick_at"))},
        "decisiones_recientes": decisions,
        "bloqueos_recientes": blocks_recent,
        "lanzadas_recientes": started_recent,
    }


def findings_for(pid: str, title: str, s: dict[str, Any], *,
                 interval_min: int = 30) -> list[Finding]:
    """Reglas → hallazgos. Cada regla nació de un fallo REAL observado en vivo."""
    out: list[Finding] = []
    loop = s["loop"]

    # 0. LA MÁS GRAVE: la fábrica no ejecuta porque está DESCONECTADA, no porque
    #    el método sea difícil. Va primero a propósito: mientras esto siga así,
    #    todo lo demás (rondas, hipótesis, planes) es trabajo que no puede cerrar
    #    ni una sola pregunta. Vivido el 2026-08-21: ~10 h en vacío por una
    #    sesión de codegen expirada.
    if s.get("fabrica_infra_caida", 0) >= 3:
        out.append(Finding(
            "INFRA_CAIDA", SEV_BUG, pid, title,
            f"{s['fabrica_infra_caida']} experimento(s) NO se ejecutaron por fallo "
            f"de credenciales/red (de {s.get('fabrica_no_ejecutados', 0)} sin ejecutar)",
            "AVERÍA, no límite científico: el agente que escribe el código de los "
            "experimentos perdió la sesión. Ningún experimento puede correr hasta "
            "reautenticar — el programa solo puede planear. Requiere a un HUMANO: "
            "reloguear el CLI (las credenciales no las puede renovar el programa).",
            {"infra": s["fabrica_infra_caida"],
             "sin_ejecutar": s.get("fabrica_no_ejecutados", 0)}))

    # 1. misiones zombis (el bug del 2026-08-21: 4 quedaron RUNNING 8 horas)
    if s["zombies"]:
        out.append(Finding(
            "MISIONES_ZOMBIS", SEV_BUG, pid, title,
            f"{len(s['zombies'])} misión(es) en RUNNING sin latido reciente "
            f"(la más vieja: {max(z['hb_age_s'] for z in s['zombies'])}s)",
            "Bloquean el candado de su hipótesis: ninguna misión nueva puede "
            "arrancar ahí. El watchdog debería recuperarlas; si reaparecen, hay "
            "un bug en la recuperación, no un accidente.",
            {"misiones": s["zombies"][:5]}))

    # 2. Centinela declarado vivo pero sin tickear (hilo muerto).
    #    OJO: se mide contra el intervalo REAL del Centinela (ACERO_PI_INTERVAL_SEC,
    #    30 min por defecto), NO contra cada cuánto corre el auditor. Confundir
    #    ambos daba un falso positivo a los ~50 min (visto el 2026-08-21) — y un
    #    auditor que grita en falso erosiona la confianza en TODOS sus hallazgos.
    #    Se suma el backoff: tras rondas secas el Centinela espera a propósito
    #    más tiempo, y eso es diseño, no avería.
    tick_h = loop.get("ultimo_tick_h")
    from .research_loop import DEFAULT_INTERVAL_SEC, DRY_BACKOFF_CAP_SEC
    dry = int(loop.get("dry_streak") or 0)
    esperado_s = min(DRY_BACKOFF_CAP_SEC, DEFAULT_INTERVAL_SEC * (2 ** dry)) \
        if dry else DEFAULT_INTERVAL_SEC
    umbral_h = (esperado_s / 3600.0) * STALE_TICK_FACTOR
    if loop.get("status") == "running" and not loop.get("paused") and \
            tick_h is not None and tick_h > umbral_h:
        out.append(Finding(
            "CENTINELA_MUDO", SEV_BUG, pid, title,
            f"el Centinela dice 'running' pero su último tick fue hace "
            f"{tick_h:.1f} h (esperado: cada ~{esperado_s / 60:.0f} min"
            + (f", con backoff por {dry} ronda(s) seca(s)" if dry else "") + ")",
            "El hilo murió sin actualizar su estado (reinicio del portal, "
            "excepción no capturada). Revisar el auto-revive y los logs.",
            {"ticks": loop.get("ticks"), "umbral_h": round(umbral_h, 2)}))

    # 2b. cola saturada: hay MUCHO más encolado de lo que el pool puede procesar.
    #     2026-08-21: 68 misiones activas con 4 workers (~2,8 h de espera) y un
    #     proyecto con 40 PENDING y CERO corriendo. Acumular no acelera.
    activas = s["misiones"].get("PENDING", 0) + s["misiones"].get("RUNNING", 0)
    corriendo = s["misiones"].get("RUNNING", 0)
    try:
        from .missions import MAX_MISSIONS
        cap_pool = MAX_MISSIONS
    except Exception:  # noqa: BLE001
        cap_pool = 4
    if activas > cap_pool * 4:
        out.append(Finding(
            "COLA_SATURADA", SEV_STALL, pid, title,
            f"{activas} misión(es) encoladas/corriendo para {cap_pool} worker(s) "
            f"— {corriendo} realmente en marcha",
            "El panel dice 'activas' pero la mayoría solo espera turno. Encolar "
            "más no acelera: conviene dejar drenar la cola antes de aprobar más "
            "hipótesis, y revisar si un proyecto está acaparando los workers.",
            {"activas": activas, "corriendo": corriendo, "workers": cap_pool}))

    # 3. giro en vacío: tickea pero nada corre
    if loop.get("dry_streak", 0) >= DRY_STREAK_ALERT:
        out.append(Finding(
            "GIRO_EN_VACIO", SEV_STALL, pid, title,
            f"{loop['dry_streak']} rondas seguidas sin lanzar NADA ejecutable",
            "El loop gasta decisiones sin producir trabajo. O el gate EVA "
            "rechaza todo, o no quedan hipótesis viables: toca redirigir el "
            "foco, no insistir con el mismo ángulo.",
            {}))

    # 4. actividad sin conocimiento: el síntoma que Merari vio a ojo
    lv = s.get("ultimo_veredicto_h")
    running = s["misiones"].get("RUNNING", 0) + s["misiones"].get("PENDING", 0)
    if running and (lv is None or lv > NO_VERDICT_HOURS):
        out.append(Finding(
            "SIN_VEREDICTOS", SEV_STALL, pid, title,
            (f"{running} misión(es) activas y "
             + (f"el último veredicto fue hace {lv:.1f} h"
                if lv is not None else "NINGÚN veredicto registrado aún")),
            "Se está gastando cómputo sin cerrar preguntas. Verificar que los "
            "experimentos terminan y escriben veredicto; si terminan sin "
            "veredicto, el paso de síntesis está roto.",
            {"misiones_activas": running}))

    # 5. bucle de decisión: la misma jugada una y otra vez
    dec = s.get("decisiones_recientes") or []
    if len(dec) >= REPEAT_DECISION_ALERT and len(set(dec)) == 1 and dec[0]:
        out.append(Finding(
            "BUCLE_DE_DECISION", SEV_DRIFT, pid, title,
            f"las últimas {len(dec)} decisiones fueron todas '{dec[0]}'",
            "El director repite jugada sin cambiar de ángulo. Conviene forzar "
            "diversidad (euler/davinci/reinterpretar) o revisar si el estado "
            "que lee ya no distingue una ronda de otra.",
            {"decisiones": dec}))

    # 6. todo bloqueado por EVA: trabaja pero nada pasa el filtro
    if s.get("bloqueos_recientes", 0) >= 3 and s.get("lanzadas_recientes", 0) == 0:
        out.append(Finding(
            "TODO_BLOQUEADO", SEV_DRIFT, pid, title,
            f"{s['bloqueos_recientes']} bloqueos y 0 lanzamientos en las "
            "últimas rondas",
            "Las hipótesis que se generan no pasan la compuerta epistémica. "
            "El problema NO es la compuerta (es soberana): es que el foco de "
            "generación produce enunciados vagos o triviales.",
            {}))

    # 7. backlog inflado: el dictamen no está corriendo
    prop = s["hipotesis"].get("PROPOSED", 0)
    cap = int(os.environ.get("ACERO_PI_MAX_PROPOSED", "15"))
    if prop > cap * BACKLOG_FACTOR:
        out.append(Finding(
            "BACKLOG_INFLADO", SEV_STALL, pid, title,
            f"{prop} hipótesis PROPOSED sin dictaminar (tope configurado: {cap})",
            "El triaje de Bohr no está reduciendo el backlog. Verificar que el "
            "dictamen corre en cada tick y que no está fallando en silencio.",
            {"propuestas": prop, "tope": cap}))

    # 8. fallos en cascada: más misiones fallan que terminan
    failed, done = s["misiones"].get("FAILED", 0), s["misiones"].get("DONE", 0)
    if failed >= 3 and failed > done:
        out.append(Finding(
            "FALLOS_EN_CASCADA", SEV_BUG, pid, title,
            f"{failed} misiones FALLIDAS vs {done} completadas",
            "Un fallo sistemático (datos inaccesibles, codegen roto, timeout "
            "mal puesto), no mala suerte. Revisar el error del último paso "
            "fallido: se repite igual en todas.",
            {"fallidas": failed, "completas": done}))

    # 9. misiones que no avanzan (worker vivo pero pegado)
    if s["estancadas"]:
        out.append(Finding(
            "MISIONES_PEGADAS", SEV_STALL, pid, title,
            f"{len(s['estancadas'])} misión(es) llevan horas por debajo del 30%",
            "Un paso largo puede ser legítimo (Turing con presupuesto), pero "
            "varias a la vez sugieren un cuello de botella o un timeout que "
            "nunca dispara.",
            {"misiones": s["estancadas"][:5]}))

    return out


_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnostico": {"type": "string"},
        "prioridad": {"type": "array", "items": {"type": "string"}},
        "redirigir": {"type": "string"},
        "salud": {"type": "string", "enum": ["sano", "atención", "grave"]},
    },
    "required": ["diagnostico", "salud"],
    "additionalProperties": False,
}

_JUDGE_SYS = (
    "Eres Bohr auditando el PROGRAMA que diriges (no una conjetura concreta). "
    "Te doy hallazgos MECÁNICOS medidos sobre el ledger: son hechos, no "
    "opiniones. Tu trabajo: (1) decir en una frase qué está pasando de verdad; "
    "(2) ordenar por prioridad qué atender primero; (3) si el programa trabaja "
    "pero apunta mal, decir hacia dónde redirigir. Regla dura: actividad NO es "
    "progreso — generar hipótesis es barato, cerrar preguntas con veredicto es "
    "lo que cuenta. Si no hay señales, di que está sano y no inventes trabajo."
)


def _deterministic_judgement(findings: list[Finding]) -> dict[str, Any]:
    """Dictamen sin LLM: mecánico y honesto (nunca inventa un problema)."""
    if not findings:
        return {"diagnostico": "sin señales de alarma: el programa avanza sin "
                               "bugs ni bucles detectables",
                "prioridad": [], "redirigir": "", "salud": "sano",
                "via": "determinístico"}
    bugs = [f for f in findings if f.severity == SEV_BUG]
    order = sorted(findings,
                   key=lambda f: {SEV_BUG: 0, SEV_STALL: 1, SEV_DRIFT: 2}.get(
                       f.severity, 3))
    return {
        "diagnostico": (f"{len(findings)} hallazgo(s): "
                        + "; ".join(f"{f.code} en {f.project_title[:28]}"
                                    for f in order[:3])),
        "prioridad": [f.code for f in order[:5]],
        "redirigir": next((f.recommendation for f in findings
                           if f.severity == SEV_DRIFT), ""),
        "salud": "grave" if bugs else "atención",
        "via": "determinístico",
    }


def _judge(findings: list[Finding], provider: Any) -> dict[str, Any]:
    ok = provider is not None and getattr(provider, "available", lambda: False)()
    if ok and findings:
        try:
            payload = json.dumps([asdict(f) for f in findings],
                                 ensure_ascii=False)[:3000]
            out = provider.complete_json(
                _JUDGE_SYS + "\n\nHALLAZGOS (JSON):\n" + payload,
                _JUDGE_SCHEMA, temperature=0.2)
            if isinstance(out, dict) and out.get("diagnostico"):
                return {**out, "via": "bohr_llm"}
        except Exception:  # noqa: BLE001 - la auditoría nunca se detiene por el LLM
            pass
    return _deterministic_judgement(findings)


def _safe_autocorrect(findings: list[Finding]) -> list[str]:
    """Correcciones AUTOMÁTICAS: solo seguras e idempotentes. El programa jamás
    reescribe su código ni borra datos — eso queda para el humano.

    EL AUDITOR OBSERVA, NO EJECUTA: el watchdog corre en modo diagnóstico
    (submit=False). Relanzar misiones desde aquí colgaba el proceso efímero
    horas — los hilos del pool no son daemon, así que el intérprete esperaba a
    que terminara una misión científica completa antes de poder salir. Quien
    debe ejecutar es el portal, que está vivo y llama al watchdog por su cuenta."""
    done: list[str] = []
    if any(f.code in ("MISIONES_ZOMBIS", "MISIONES_PEGADAS") for f in findings):
        try:
            from .missions import MissionEngine
            r = MissionEngine().watchdog(submit=False)
            n_res, n_reap = len(r.get("resumed", [])), len(r.get("reaped", []))
            done.append(
                f"watchdog (diagnóstico): {n_res} misión(es) recuperables, "
                f"{n_reap} dadas por muertas"
                + (" — el portal las retomará en su próximo barrido" if n_res else ""))
        except Exception as exc:  # noqa: BLE001
            done.append(f"watchdog falló: {str(exc)[:120]}")
    return done


def supervision_dir() -> Path:
    """Los informes viven en el ESPACIO DE TRABAJO, nunca en el repo."""
    env = os.environ.get("ACERO_SUPERVISION_DIR", "").strip()
    if env:
        d = Path(env)
    else:
        from ..core.workspace import data_path
        d = Path(data_path("supervision"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def supervise_once(*, sf: Any = None, provider: Any = None,
                   interval_min: int = 30, write: bool = True) -> dict[str, Any]:
    """Una pasada completa: hechos → hallazgos → juicio → correcciones seguras."""
    from ..discovery.store import DiscoveryStore
    from ..ledger.db import default_session_factory
    from ..ledger.service import ResearchLedger
    from .research_loop import load_state, recent_feedback

    sf = sf or default_session_factory()
    lg = ResearchLedger(sf)
    store = DiscoveryStore(sf, lg)

    findings: list[Finding] = []
    per_project: list[dict[str, Any]] = []
    for p in lg.list_projects():
        pid = p.id
        title = str(getattr(p, "title", "") or pid)
        try:
            st = load_state(pid)
            # solo auditamos lo VIVO: un proyecto en pausa no es un problema
            if st.get("paused") or st.get("status") not in ("running",):
                continue
            fb = recent_feedback(pid, 8)
            sig = project_signals(store, pid, loop_state=st, feedback=fb)
            fnd = findings_for(pid, title, sig, interval_min=interval_min)
            findings.extend(fnd)
            per_project.append({"project_id": pid, "title": title,
                                "signals": sig,
                                "findings": [f.code for f in fnd]})
        except Exception as exc:  # noqa: BLE001 - un proyecto roto no frena la auditoría
            per_project.append({"project_id": pid, "title": title,
                                "error": str(exc)[:200]})

    if provider is None and os.environ.get("ACERO_SUP_NO_LLM") != "1":
        try:
            from ..llm.providers import CodexCliProvider
            # Timeout CORTO a propósito: en cron, una auditoría que tarda más que
            # su propio intervalo se solapa consigo misma. Los hallazgos (lo
            # valioso) ya están calculados; el juicio del LLM es un extra que
            # puede caer al determinístico sin perder nada verificable.
            provider = CodexCliProvider(
                timeout_sec=int(os.environ.get("ACERO_SUP_LLM_TIMEOUT", "90")))
        except Exception:  # noqa: BLE001
            provider = None
    judgement = _judge(findings, provider)
    actions = _safe_autocorrect(findings)

    report = {
        "id": new_id("sup"), "ts": now_iso(),
        "proyectos_vivos": len(per_project),
        "n_hallazgos": len(findings),
        "hallazgos": [asdict(f) for f in findings],
        "juicio": judgement,
        "correcciones_automaticas": actions,
        "detalle": per_project,
    }
    if write:
        try:
            d = supervision_dir()
            (d / f"{report['id']}.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            # 'ultimo.json' = el que lee el humano/agente sin buscar
            (d / "ultimo.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001 - escribir el informe nunca rompe la pasada
            pass
    return report


def run_supervision(*, hours: float = 8.0, every_min: int = 15,
                    sf: Any = None, provider: Any = None,
                    sleeper: Any = time.sleep, clock: Any = time.time,
                    max_passes: int | None = None) -> dict[str, Any]:
    """Driver: audita cada `every_min` durante `hours` y se apaga solo.

    Se auto-expira por diseño: una supervisión que corre para siempre deja de
    ser una revisión y se vuelve ruido de fondo que nadie lee."""
    deadline = clock() + hours * 3600.0
    passes, reports = 0, []
    while clock() < deadline:
        rep = supervise_once(sf=sf, provider=provider, interval_min=every_min)
        reports.append({"id": rep["id"], "ts": rep["ts"],
                        "n_hallazgos": rep["n_hallazgos"],
                        "salud": rep["juicio"].get("salud")})
        passes += 1
        if max_passes is not None and passes >= max_passes:
            break
        if clock() + every_min * 60 >= deadline:
            break
        sleeper(every_min * 60)
    return {"passes": passes, "reports": reports}
