"""Guardián de premisa y jerarquía — el POR QUÉ de una investigación es sagrado.

Lección aprendida en vivo (Erdős–Straus, rondas 1-4): la pregunta original era
jerárquica — PORQUÉ: construir una llave DINÁMICA k(p) cuya fórmula incorpore el
crecimiento; MEDIO: entender cómo crece cover(N) con N; DEFINICIÓN: el criterio
FUERTE del divisor (t | (p·x)² con t ≡ −px mod k). Entre rondas, sin que nadie lo
decidiera, la definición se degradó a la trivialidad p+k≡0 (mod 4), el medio se
volvió el fin, y el porqué desapareció. La Ronda 4 gastó 51 jugadas y 13 h de CPU
demostrando lemas sobre una cerradura que no era la cerradura.

Este módulo aplica al enunciado mismo el mecanismo que ACERO ya usa para los
protocolos (pre-registro sellado, CCC-1):

  * `seal_premise()`  — al abrir la investigación se fija porqué / medio /
    definiciones. Queda SELLADO en el ledger (kind='premise'). Inmutable: sellar
    de nuevo crea una versión nueva, nunca edita la anterior.
  * `premise_context()` — el bloque de texto NO NEGOCIABLE que Bohr ve en cada
    decisión. Reformular está permitido; debilitar definiciones o perder el
    porqué, no.
  * `check_drift()` — cada vez que el enunciado operativo cambia (reinicio de
    Bohr, refinamiento de Feynman), se contrasta contra el sello. La deriva se
    registra como kind='drift' y se inyecta al contexto de Bohr como alerta.

El guardián NO bloquea al programa (no es un límite): hace la deriva VISIBLE y
obliga a que cambiar la premisa sea una decisión explícita del humano, no una
erosión silenciosa entre rondas.
"""

from __future__ import annotations

import time
from typing import Any

from ..core.ids import new_id

DRIFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "deriva": {"type": "boolean",
                   "description": "true si el enunciado debilita/abandona la premisa"},
        "severidad": {"type": "string", "enum": ["ninguna", "leve", "grave"],
                      "description": "grave = definición sustituida por una más débil "
                                     "o porqué perdido; leve = medio atacado sin "
                                     "mencionar el fin"},
        "que_se_debilito": {"type": "string",
                            "description": "qué parte del sello se degradó y cómo "
                                           "(vacío si no hay deriva)"},
        "razon": {"type": "string",
                  "description": "explicación corta y concreta"},
    },
    "required": ["deriva", "severidad", "que_se_debilito", "razon"],
    "additionalProperties": False,     # Codex exige esquemas estrictos
}

_DRIFT_SYS = """Eres el guardián de premisa de ACERO. Te doy la PREMISA SELLADA de una
investigación (porqué / medio / definiciones operativas exactas) y un ENUNCIADO nuevo
que el ciclo quiere adoptar. Tu único trabajo: decidir si el enunciado DERIVA.

DERIVA GRAVE:
- sustituye una definición sellada por una más débil (ej.: cambiar un criterio de
  divisores por una mera condición de paridad/congruencia que era solo el requisito
  de buena formación);
- abandona el porqué (ataca otra cosa sin conexión declarada con el objetivo).
DERIVA LEVE:
- ataca el medio como si fuera el fin, sin decir cómo alimenta al porqué.
NO ES DERIVA:
- reformular con otras palabras manteniendo las definiciones con su fuerza;
- atacar un sub-lema declarando explícitamente cómo sirve al porqué;
- restringir a un caso particular COMO PASO declarado hacia el general.
Sé estricto con las definiciones: si el sello exige un criterio y el enunciado usa
otro más flojo, es deriva grave aunque suene parecido."""


def _store(sf: Any = None) -> Any:
    from ..discovery.store import DiscoveryStore
    from ..ledger.db import default_session_factory
    from ..ledger.service import ResearchLedger
    factory = sf or default_session_factory()
    return DiscoveryStore(factory, ResearchLedger(factory))


def seal_premise(project_id: str, *, porque: str, medio: str,
                 definiciones: dict[str, str], sf: Any = None) -> str:
    """Sella la premisa de la investigación. Devuelve el id del sello.

    `porque`: el objetivo real e irrenunciable (ej.: llave dinámica k(p)).
    `medio`: el camino instrumental (ej.: ley de crecimiento de cover(N)).
    `definiciones`: nombre → definición operativa EXACTA, con su fuerza completa.
    """
    store = _store(sf)
    version = len(store.list_objects(project_id, kind="premise")) + 1
    pid_seal = f"prem_{project_id[-8:]}_{version}"
    store.put(project_id, "premise", pid_seal,
              {"id": pid_seal, "version": version, "porque": porque.strip(),
               "medio": medio.strip(),
               "definiciones": {k: v.strip() for k, v in definiciones.items()},
               "sealed_at": time.time(), "origin": "guardian-premisa"},
              status="SEALED", actor="Hilbert",
              summary=f"premisa sellada v{version}: {porque[:90]}")
    return pid_seal


def get_premise(project_id: str, sf: Any = None) -> dict[str, Any] | None:
    """La premisa sellada MÁS RECIENTE del proyecto (None si nunca se selló)."""
    seals = _store(sf).list_objects(project_id, kind="premise")
    if not seals:
        return None
    return max(seals, key=lambda s: int(s.get("version") or 0))


def premise_context(premise: dict[str, Any]) -> str:
    """El bloque que Bohr ve en cada decisión. No negociable."""
    defs = "\n".join(f"  - {k}: {v}"
                     for k, v in (premise.get("definiciones") or {}).items())
    return (
        "PREMISA SELLADA (v%s) — NO NEGOCIABLE. La jerarquía es: el PORQUÉ manda, "
        "el medio lo sirve, las definiciones no se debilitan JAMÁS sin decisión "
        "humana explícita.\n"
        "PORQUÉ (objetivo irrenunciable): %s\n"
        "MEDIO (instrumental, no es el fin): %s\n"
        "DEFINICIONES OPERATIVAS EXACTAS (usar SIEMPRE con su fuerza completa):\n%s\n"
        "Si una jugada necesita otra definición, debe DECLARARLO como desviación y "
        "justificar cómo sigue sirviendo al porqué — nunca sustituir en silencio."
        % (premise.get("version"), premise.get("porque"),
           premise.get("medio"), defs or "  (sin definiciones)")
    )


def check_drift(provider: Any, premise: dict[str, Any], statement: str,
                *, project_id: str = "", parent_id: str | None = None,
                sf: Any = None) -> dict[str, Any]:
    """Contrasta un enunciado nuevo contra el sello; registra la deriva si la hay.

    Nunca lanza: si el proveedor falla, devuelve un resultado honesto marcado
    `sin_revision` — no revisar NO cuenta como aprobar."""
    prompt = (f"{_DRIFT_SYS}\n\n=== PREMISA SELLADA ===\n{premise_context(premise)}\n\n"
              f"=== ENUNCIADO NUEVO ===\n{statement}")
    try:
        out = provider.complete_json(prompt, DRIFT_SCHEMA, temperature=0.1)
    except Exception as exc:  # noqa: BLE001 - guardián caído ≠ aprobación
        return {"deriva": False, "severidad": "ninguna", "que_se_debilito": "",
                "razon": f"guardián sin revisión (proveedor caído: {str(exc)[:120]}) "
                         "— NO cuenta como aprobación", "sin_revision": True}
    result = {"deriva": bool(out.get("deriva")),
              "severidad": str(out.get("severidad") or "ninguna"),
              "que_se_debilito": str(out.get("que_se_debilito") or ""),
              "razon": str(out.get("razon") or ""), "sin_revision": False}
    if result["deriva"] and project_id:
        store = _store(sf)
        # new_id() (timestamp + os.urandom) y NO f"drift_{int(time.time()*1000)}":
        # dos derivas registradas en el mismo milisegundo compartían id y la
        # segunda pisaba a la primera en el store — count_grave() subcontaba
        # las derivas graves reales (visto en tests que corren check_drift en
        # ráfaga: 4 llamadas rápidas solo dejaban 3 ids distintos).
        store.put(project_id, "drift", new_id("drift"),
                  {**result, "statement": statement[:500],
                   "premise_version": premise.get("version"),
                   "origin": "guardian-premisa"},
                  status="FLAGGED", parent_id=parent_id, actor="Hilbert",
                  summary=f"DERIVA {result['severidad']}: "
                          f"{result['que_se_debilito'][:100]}")
    return result


def count_grave(project_id: str, sf: Any = None,
                premise_version: int | None = None) -> int:
    """Cuántas derivas GRAVES lleva esta investigación CONTRA EL SELLO VIGENTE.

    El filtro por versión no es cosmético. "Dirección bloqueada" significa *el
    ciclo insiste en empujar contra este sello*, y eso deja de tener sentido en
    cuanto un humano cambia el sello: las derivas viejas se juzgaron contra una
    premisa que ya no rige.

    Aprendido en vivo (Erdős–Straus, 2026-08-11): el MEDIO sellado era "la ley de
    crecimiento de cover(N)", y nuestro propio cómputo mató ese objeto — en 1e11
    apareció una puerta huérfana y el cover con llavero acotado dejó de existir.
    A partir de ahí el guardián exigía conectar cada jugada con un crecimiento
    que ya no había, y marcaba grave hasta a las jugadas SANAS: la última pedía
    exactamente una llave dinámica con mecanismo y criterio fuerte intacto.
    Quince graves acumuladas. Si al resellar siguieran contando, el reselle no
    destrabaría nada y el humano habría decidido en vano.

    Sin versión explícita se usa la del sello vigente. Si un drift no la trae
    (los de antes de este campo), se cuenta: preferimos bloquear de más a dejar
    pasar una deriva por un dato ausente."""
    try:
        objetos = _store(sf).list_objects(project_id, kind="drift")
        vigente = premise_version
        if vigente is None:
            prem = get_premise(project_id, sf=sf)
            vigente = int(prem.get("version") or 0) if prem else 0
        # Estados de adjudicación que CIERRAN una deriva (decisión humana del
        # 2026-08-19, run 3): el evento queda intacto en el ledger, pero una
        # deriva adjudicada ya no cuenta contra el sello. Sin `estado` (o con
        # ACTIVE / HUMAN_DECISION_REQUIRED) sigue contando: bloquear de más
        # antes que dejar pasar.
        cerradas = {"RESOLVED", "RESOLVED_BY_FIX", "RESOLVED_BY_SCOPE",
                    "SCIENTIFIC_LINE_REJECTED", "MOVED_TO_SEPARATE_PROGRAM"}
        n = 0
        for d in objetos:
            if d.get("severidad") != "grave":
                continue
            if str(d.get("estado") or "").upper() in cerradas:
                continue
            v = d.get("premise_version")
            if v is None or int(v) == vigente:
                n += 1
        return n
    except Exception:  # noqa: BLE001
        return 0


# A partir de esta cantidad de derivas graves, la dirección se considera
# BLOQUEADA: no es que una jugada se equivocara, es que el ciclo insiste en
# empujar hacia donde el sello no deja.
GRAVE_BLOCK_THRESHOLD = 3


def drift_warning(result: dict[str, Any], *, n_grave: int = 0) -> str:
    """Línea de alerta para inyectar al historial que Bohr lee.

    ESCALADA (aprendida en vivo, Ronda 5): el guardián marcaba cada deriva por
    separado y Bohr reintentaba una variante de lo mismo — cinco veces seguidas.
    Marcar sin escalar no rompe un bucle: el guard anti-bucle de Bohr exige
    resúmenes IDÉNTICOS y estas reformulaciones cambian de texto cada vez. A
    partir del umbral, la alerta deja de ser advertencia y pasa a declarar la
    dirección BLOQUEADA."""
    if not result.get("deriva"):
        return ""
    base = (f"⚠️ ALERTA DEL GUARDIÁN DE PREMISA [{result.get('severidad')}]: "
            f"{result.get('que_se_debilito')} — {result.get('razon')} ")
    if result.get("severidad") == "grave" and n_grave >= GRAVE_BLOCK_THRESHOLD:
        return (base + f"🛑 DIRECCIÓN BLOQUEADA: van {n_grave} derivas GRAVES en "
                "esta investigación, todas empujando contra el sello. NO vuelvas a "
                "reformular hacia ahí: cambia de ENFOQUE (otra representación, otro "
                "sub-problema que sí alimente el porqué) o CIERRA con disposición "
                "honesta y deja la decisión al humano. Insistir es gastar el "
                "presupuesto en una dirección que el sello ya rechazó.")
    return (base + "El enunciado NO respeta el sello: corrige la jugada o declara "
            "la desviación explícitamente.")
