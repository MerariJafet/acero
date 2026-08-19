"""Guardián de premisa: el porqué es sagrado, las definiciones no se debilitan solas.

Contexto real: en Erdős–Straus la jerarquía era porqué=llave dinámica k(p),
medio=ley de crecimiento del cover, definición=criterio del divisor t|(px)² con
t≡−px (mod k). Entre rondas la definición se degradó a p+k≡0 (mod 4) sin que
nadie lo decidiera y la Ronda 4 gastó 51 jugadas en la cerradura equivocada.
Estos tests fijan que esa erosión ya no puede ser silenciosa."""

from __future__ import annotations

from typing import Any

from acero.portal.premise import (check_drift, drift_warning, get_premise,
                                  premise_context, seal_premise)


class _Prov:
    def __init__(self, answer: dict[str, Any] | Exception) -> None:
        self._a = answer
        self.prompts: list[str] = []

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0
                      ) -> dict:
        self.prompts.append(prompt)
        if isinstance(self._a, Exception):
            raise self._a
        return self._a


def _sello(session_factory) -> tuple[str, dict]:
    from acero.ledger.service import ResearchLedger
    p = ResearchLedger(session_factory).create_project("premisa", domain="math")
    seal_premise(
        p.id, sf=session_factory,
        porque="construir una llave DINÁMICA k(p) que se adapte al crecimiento",
        medio="ley de crecimiento de cover(N)",
        definiciones={"C(p,k)": "existe t | (p·x)² con t ≡ −px (mod k), x=(p+k)/4"})
    return p.id, get_premise(p.id, sf=session_factory)


def test_sellar_y_leer_premisa(session_factory) -> None:
    pid, prem = _sello(session_factory)
    assert prem["version"] == 1 and "DINÁMICA" in prem["porque"]
    ctx = premise_context(prem)
    assert "NO NEGOCIABLE" in ctx and "t ≡ −px" in ctx and "PORQUÉ" in ctx


def test_resellar_crea_version_nueva_no_edita(session_factory) -> None:
    pid, _ = _sello(session_factory)
    seal_premise(pid, sf=session_factory, porque="v2 del porqué", medio="m",
                 definiciones={})
    prem = get_premise(pid, sf=session_factory)
    assert prem["version"] == 2 and prem["porque"] == "v2 del porqué"


def test_deriva_grave_se_registra_en_el_ledger(session_factory) -> None:
    """El caso EXACTO que pasó: sustituir el criterio del divisor por mod 4."""
    pid, prem = _sello(session_factory)
    prov = _Prov({"deriva": True, "severidad": "grave",
                  "que_se_debilito": "C(p,k) degradado a p+k≡0 mod 4",
                  "razon": "la condición de paridad es solo el requisito de buena "
                           "formación, no la cerradura"})
    res = check_drift(prov, prem, "Definir C(p,k)=1 sii p+k≡0 mod 4 y probar…",
                      project_id=pid, sf=session_factory)
    assert res["deriva"] is True and res["severidad"] == "grave"
    warn = drift_warning(res)
    assert "GUARDIÁN" in warn and "mod 4" in warn
    # quedó en el ledger como kind='drift' para el dashboard y para Bohr
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    drifts = st.list_objects(pid, kind="drift")
    assert len(drifts) == 1 and "mod 4" in drifts[0]["que_se_debilito"]
    # y el sello COMPLETO viajó en el prompt del guardián
    assert "t ≡ −px" in prov.prompts[0]


def test_sin_deriva_no_ensucia_el_ledger(session_factory) -> None:
    pid, prem = _sello(session_factory)
    prov = _Prov({"deriva": False, "severidad": "ninguna",
                  "que_se_debilito": "", "razon": "reformula sin debilitar"})
    res = check_drift(prov, prem, "Mismo criterio del divisor, restringido a p<10^6 "
                                  "como paso declarado hacia el caso general",
                      project_id=pid, sf=session_factory)
    assert res["deriva"] is False and drift_warning(res) == ""
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    assert st.list_objects(pid, kind="drift") == []


def test_guardian_caido_no_cuenta_como_aprobacion(session_factory) -> None:
    pid, prem = _sello(session_factory)
    res = check_drift(_Prov(RuntimeError("llm caído")), prem, "lo que sea",
                      project_id=pid, sf=session_factory)
    assert res["sin_revision"] is True and res["deriva"] is False
    assert "NO cuenta como aprobación" in res["razon"]


def test_bohr_ve_el_sello_y_la_alerta_en_reinicios(session_factory) -> None:
    """Integración: run_bohr_cycle con premisa sellada — el conocimiento de Bohr
    abre con el sello, y un 'reiniciar' que deriva queda marcado en el historial."""
    from acero.portal.investigator_bridge import run_bohr_cycle
    from acero.science.bohr import BohrOrchestrator

    pid, prem = _sello(session_factory)
    captured: dict[str, Any] = {}

    class _FakeOrch:
        def run(self, claim: str) -> dict[str, Any]:
            return {"disposition": "dropped", "close_reason": "test",
                    "statement": claim, "history": [], "n_actions": 0,
                    "elapsed_s": 0.1}

    class _FakeProv:
        def complete_json(self, prompt: str, schema: dict, *,
                          temperature: float = 0.0) -> dict:
            props = set((schema.get("properties") or {}).keys())
            if "deriva" in props:
                return {"deriva": True, "severidad": "grave",
                        "que_se_debilito": "criterio sustituido",
                        "razon": "definición más débil"}
            if "siguiente_claim" in props:
                return {"hilos_no_explorados": [], "pista_pendiente": "",
                        "siguiente_claim": "", "razon": ""}
            return {}

    out = run_bohr_cycle(pid, "claim con premisa", provider=_FakeProv(),
                         orchestrator=_FakeOrch(), sf=session_factory)
    assert out["disposition"] == "dropped"

    # ahora directo el orquestador real: on_restart anexa la alerta al historial
    def _guard(stmt: str) -> str:
        return "⚠️ ALERTA DEL GUARDIÁN DE PREMISA [grave]: criterio sustituido"

    class _Scripted:
        def __init__(self) -> None:
            self._n = 0

        def complete_json(self, prompt: str, schema: dict, *,
                          temperature: float = 0.0) -> dict:
            self._n += 1
            if self._n == 1:
                return {"action": "reiniciar", "reason": "cambio de enunciado",
                        "statement": "enunciado DEBILITADO", "expected": "",
                        "frontier": "", "why_stuck": "", "idea": "", "piezas": [],
                        "budget_min": 0, "disposition": ""}
            return {"action": "cerrar", "reason": "fin", "statement": "",
                    "expected": "", "frontier": "", "why_stuck": "", "idea": "",
                    "piezas": [], "budget_min": 0, "disposition": "dropped"}

    res = BohrOrchestrator(_Scripted(), {}, on_restart=_guard).run("original")
    assert any("GUARDIÁN" in str(h.get("summary")) for h in res["history"])


def test_derivas_graves_repetidas_escalan_a_bloqueo(session_factory) -> None:
    """Aprendido EN VIVO (Ronda 5): el guardián marcaba cada deriva por separado
    y Bohr reintentaba una variante de lo mismo cinco veces. El guard anti-bucle
    de Bohr no ayuda porque exige resúmenes idénticos y cada reformulación cambia
    de texto. A partir del umbral la alerta declara la dirección BLOQUEADA."""
    from acero.portal.premise import (GRAVE_BLOCK_THRESHOLD, count_grave,
                                      drift_warning)
    grave = {"deriva": True, "severidad": "grave",
             "que_se_debilito": "sustituyó el criterio", "razon": "más flojo"}
    # las primeras avisan
    w1 = drift_warning(grave, n_grave=1)
    assert "ALERTA" in w1 and "BLOQUEADA" not in w1
    # al acumularse, BLOQUEAN
    w3 = drift_warning(grave, n_grave=GRAVE_BLOCK_THRESHOLD)
    assert "DIRECCIÓN BLOQUEADA" in w3
    assert "cambia de ENFOQUE" in w3 and "CIERRA" in w3
    # una deriva LEVE nunca escala, por muchas graves que haya
    leve = {**grave, "severidad": "leve"}
    assert "BLOQUEADA" not in drift_warning(leve, n_grave=9)
    # y sin deriva no hay alerta
    assert drift_warning({"deriva": False}, n_grave=9) == ""

    pid, prem = _sello(session_factory)
    assert count_grave(pid, sf=session_factory) == 0


def test_resellar_limpia_el_bloqueo_pero_no_borra_la_historia(session_factory) -> None:
    """Aprendido EN VIVO (2026-08-11): el MEDIO sellado era la ley de crecimiento
    de cover(N), y nuestro propio cómputo mató ese objeto — en 1e11 apareció una
    puerta huérfana y el cover con llavero acotado dejó de existir. El guardián
    siguió exigiendo conectar cada jugada con un crecimiento inexistente y marcó
    grave hasta jugadas SANAS. Se acumularon quince.

    Si al resellar esas quince siguieran contando, el reselle no destrabaría nada
    y la decisión humana sería decorativa. "Dirección bloqueada" es relativo AL
    SELLO: cambiar el sello reinicia el contador, no la historia."""
    from acero.portal.premise import count_grave, get_premise, seal_premise
    pid, prem = _sello(session_factory)
    prov = _Prov({"deriva": True, "severidad": "grave",
                  "que_se_debilito": "sustituyó el criterio", "razon": "más flojo"})
    for _ in range(4):
        check_drift(prov, prem, "enunciado que deriva", project_id=pid,
                    sf=session_factory)
    assert count_grave(pid, sf=session_factory) == 4          # bloquea, con razón

    seal_premise(pid, sf=session_factory, porque="mismo porqué",
                 medio="la COLA: S(K) y las puertas que fuerzan llaves nuevas",
                 definiciones=prem["definiciones"])
    assert get_premise(pid, sf=session_factory)["version"] == 2
    assert count_grave(pid, sf=session_factory) == 0          # pizarra limpia

    # la historia NO se borra: sigue auditable en el ledger
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    viejas = st.list_objects(pid, kind="drift")
    assert len(viejas) == 4 and all(d["premise_version"] == 1 for d in viejas)

    # y una deriva NUEVA contra v2 sí cuenta
    prem2 = get_premise(pid, sf=session_factory)
    check_drift(prov, prem2, "otra que deriva", project_id=pid, sf=session_factory)
    assert count_grave(pid, sf=session_factory) == 1


def test_deriva_sin_version_cuenta_igual(session_factory) -> None:
    """Un drift viejo sin `premise_version` (anterior al campo) se cuenta:
    ante un dato ausente preferimos bloquear de más a dejar pasar."""
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.premise import count_grave
    pid, _ = _sello(session_factory)
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    st.put(pid, "drift", "drift_legacy",
           {"severidad": "grave", "que_se_debilito": "x", "razon": "y"},
           status="FLAGGED", actor="Hilbert", summary="deriva sin versión")
    assert count_grave(pid, sf=session_factory) == 1


def test_deriva_adjudicada_deja_de_contar_sin_borrarse(session_factory) -> None:
    """Decisión humana (2026-08-19, run 3): una deriva grave ADJUDICADA
    (RESOLVED_BY_SCOPE, RESOLVED_BY_FIX, SCIENTIFIC_LINE_REJECTED,
    MOVED_TO_SEPARATE_PROGRAM) deja de contar contra el sello, pero el evento
    sigue íntegro en el ledger. ACTIVE y HUMAN_DECISION_REQUIRED siguen
    contando: no se fuerza el cero."""
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.premise import count_grave

    pid, prem = _sello(session_factory)
    prov = _Prov({"deriva": True, "severidad": "grave",
                  "que_se_debilito": "optimiza el selector", "razon": "medio"})
    for _ in range(3):
        check_drift(prov, prem, "enunciado que deriva", project_id=pid,
                    sf=session_factory)
    assert count_grave(pid, sf=session_factory) == 3

    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    drifts = [r for r in st.list_rows(pid) if r["kind"] == "drift"]
    # dos adjudicadas con estados de cierre, una queda pendiente de humano
    for row, estado in zip(drifts, ("RESOLVED_BY_SCOPE",
                                    "SCIENTIFIC_LINE_REJECTED",
                                    "HUMAN_DECISION_REQUIRED")):
        pay = dict(row["payload"]); pay["estado"] = estado
        st.put(pid, "drift", row["id"], pay, status=estado)
    assert count_grave(pid, sf=session_factory) == 1
    # nada se borró
    assert len([r for r in st.list_rows(pid) if r["kind"] == "drift"]) == 3
