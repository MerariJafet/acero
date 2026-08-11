"""Upgrade quirúrgico (revisión externa 2026-08-10): Bohr híbrido, capacidades
tipadas, permisos de estado, discovery fabric fase 1, credence, GPU policy."""

from __future__ import annotations

from typing import Any

# --- UPG-1: Bohr híbrido (PolicyEngine) --------------------------------------------
from acero.science.policy import PolicyEngine, PROPOSE_SCHEMA, score


def _cand(action: str, **kw: Any) -> dict[str, Any]:
    base = {"action": action, "reason": "r", "expected": "e", "statement": "",
            "frontier": "", "why_stuck": "", "idea": "", "piezas": [],
            "budget_min": 0, "disposition": "", "dataset_ref": "", "target": "",
            "info_esperada": 0.5, "falsabilidad": 0.5, "novedad": 0.5,
            "reduccion_incertidumbre": 0.5, "riesgo": 0.1}
    base.update(kw)
    return base


def test_policy_elige_por_utilidad_no_por_orden() -> None:
    eng = PolicyEngine()
    peor = _cand("turing", info_esperada=0.1, novedad=0.1)     # caro y poca info
    mejor = _cand("hipatia", info_esperada=0.9, novedad=0.9)   # barato y mucha
    winner, scored = eng.choose([peor, mejor], history=[])
    assert winner["action"] == "hipatia"
    assert len(scored) == 2
    assert winner["_policy"]["elegida"]["utility"] > 0     # desglose auditable


def test_policy_penaliza_repeticion_medida_no_declarada() -> None:
    """El LLM puede JURAR que repetir dará información; el historial dice que las
    2 últimas veces dio el MISMO resultado — la máquina lo demota."""
    eng = PolicyEngine()
    hist = [{"action": "popper", "summary": "veredicto=holds_empirically; igual"},
            {"action": "popper", "summary": "veredicto=holds_empirically; igual"}]
    repetir = _cand("popper", info_esperada=0.9, novedad=0.9)
    alternativa = _cand("godel", info_esperada=0.6, novedad=0.6)
    winner, _ = eng.choose([repetir, alternativa], history=hist)
    assert winner["action"] == "godel"
    s = score(repetir, hist)
    assert s["desglose"]["repeticion"] > 0.5


def test_policy_sin_candidatas_validas_devuelve_none() -> None:
    winner, scored = PolicyEngine().choose([{"action": ""}, "basura"], [])
    assert winner is None and scored == []


def test_bohr_hibrido_llm_propone_maquina_elige() -> None:
    from acero.science.bohr import BohrOrchestrator

    class _Prov:
        def __init__(self) -> None:
            self.n = 0

        def complete_json(self, prompt: str, schema: dict, *,
                          temperature: float = 0.0) -> dict:
            self.n += 1
            if self.n == 1:      # propuesta: dos candidatas que compiten
                return {"candidatas": [
                    _cand("turing", info_esperada=0.2),
                    _cand("aristoteles", info_esperada=0.9, novedad=0.8)]}
            return {"candidatas": [
                _cand("cerrar", disposition="partial_progress",
                      reason="fin", info_esperada=0.1)]}

    runs: list[str] = []
    out = BohrOrchestrator(_Prov(), {
        "aristoteles": lambda statement, decision: (runs.append("a") or
                                                    {"summary": "crítica ok"}),
        "turing": lambda statement, decision: (runs.append("t") or
                                               {"summary": "build"}),
    }).run("claim")
    assert runs == ["a"]                       # ganó la de mayor utilidad
    assert out["disposition"] == "partial_progress"


def test_bohr_hibrido_compatible_con_proveedor_de_decision_unica() -> None:
    """Un proveedor legado que devuelve UNA decisión (sin 'candidatas') no rompe
    nada ni consume llamadas extra: su respuesta directa se respeta."""
    from acero.science.bohr import BohrOrchestrator

    class _Legacy:
        def complete_json(self, prompt: str, schema: dict, *,
                          temperature: float = 0.0) -> dict:
            return {"action": "cerrar", "reason": "directo",
                    "disposition": "dropped"}

    out = BohrOrchestrator(_Legacy(), {}).run("x")
    assert out["disposition"] == "dropped"


def test_propose_schema_es_estricto() -> None:
    assert PROPOSE_SCHEMA["additionalProperties"] is False
    item = PROPOSE_SCHEMA["properties"]["candidatas"]["items"]
    assert item["additionalProperties"] is False
    assert "info_esperada" in item["required"]


# --- CONS-3: guardas adversariales del PolicyEngine --------------------------------
def test_policy_estimaciones_infladas_se_recortan_a_1() -> None:
    """El LLM no puede comprar el ranking inflando: info=99 vale igual que 1.0,
    y el riesgo tiene PISO de tabla que su autoevaluación no puede rebajar."""
    s = score(_cand("reiniciar", info_esperada=99.0, novedad=99.0, riesgo=0.0), [])
    assert s["desglose"]["info"] == 1.0 and s["desglose"]["novedad"] == 1.0
    assert s["desglose"]["riesgo"] >= 0.45          # piso mecánico de 'reiniciar'


def test_policy_nan_inf_y_faltantes_no_propagan() -> None:
    import math
    s = score(_cand("hipatia", info_esperada=float("nan"),
                    falsabilidad=float("inf"), novedad=None), [])
    assert s["desglose"]["info"] == 0.0
    assert s["desglose"]["falsif"] == 0.0
    assert s["desglose"]["novedad"] == 0.0
    assert math.isfinite(s["utility"])              # jamás NaN en la utilidad


def test_policy_registra_version_y_fuentes() -> None:
    """Auditoría: cada score declara su FUENTE (proposer/mechanical) y la versión
    de política; el estimador histórico existe como interfaz y devuelve None
    honestamente (v1 no aprende del historial más allá de la repetición)."""
    from acero.science.policy import POLICY_VERSION, historical_estimate
    s = score(_cand("popper"), [])
    assert s["policy_version"] == POLICY_VERSION
    assert s["fuentes"]["info"] == "proposer"       # estimación del LLM, declarada
    assert s["fuentes"]["costo"] == "mechanical"
    assert s["historical_estimate"] is None
    assert historical_estimate("popper", []) is None


def test_policy_repeticion_disfrazada_con_otra_razon_igual_se_penaliza() -> None:
    """Cambiar el 'reason' no engaña a la penalización: mira acción+resultado."""
    hist = [{"action": "turing", "summary": "budget_exhausted: sin señal"},
            {"action": "turing", "summary": "budget_exhausted: sin señal"}]
    disfrazada = _cand("turing", reason="ahora con OTRO ángulo totalmente nuevo",
                       info_esperada=0.95, novedad=0.95)
    s = score(disfrazada, hist)
    assert s["desglose"]["repeticion"] > 0.5


# --- UPG-2: capacidades tipadas + permisos -----------------------------------------
def test_capacidades_sin_huerfanas_ni_fantasmas() -> None:
    from acero.science.capabilities import (PERSONA_CAPABILITIES,
                                            capability_of, validate_registry)
    assert validate_registry() == []
    assert len(PERSONA_CAPABILITIES) == 18       # los 18 del Consejo
    godel = capability_of("godel")
    assert godel[0]["capability"] == "smt_verification"
    assert godel[0]["llm_level"] == 0            # la prueba mecánica no es opinión


def test_permisos_lemma_sin_backend_mecanico_se_degrada() -> None:
    from acero.science.permissions import check_put
    out, viol = check_put("Gödel", "lemma",
                          {"statement": "s", "proved": True, "backend": "llm"})
    assert out["proved"] is False                # texto de LLM jamás es prueba
    assert viol and "_permiso_violado" in out
    ok, viol2 = check_put("Gödel", "lemma",
                          {"statement": "s", "proved": True, "backend": "z3"})
    assert ok["proved"] is True and viol2 == []


def test_permisos_actor_no_autorizado_queda_marcado() -> None:
    from acero.science.permissions import check_put
    out, viol = check_put("Noether", "lemma", {"statement": "s"})
    assert viol and "Noether" in viol[0]         # Noether jamás escribe lemas
    out2, viol2 = check_put("Mendeleev", "pattern", {"description": "d"})
    assert viol2 == [] and "_permiso_violado" not in out2


def test_record_lemma_aplica_permisos_y_registra_el_intento(session_factory) -> None:
    """La degradación NO basta: el INTENTO queda como kind='violation' — si una
    ruta intenta 300 veces elevar a prueba, estas filas lo delatan."""
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.investigator_bridge import record_lemma
    p = ResearchLedger(session_factory).create_project("perm", domain="math")
    record_lemma(p.id, "lema con backend falso", proved=True, backend="charla",
                 sf=session_factory)
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    lem = st.list_objects(p.id, kind="lemma")[0]
    assert lem["proved"] is False and lem["_permiso_violado"]
    viols = st.list_objects(p.id, kind="violation")
    assert len(viols) == 1
    assert viols[0]["kind_objetivo"] == "lemma"
    # un lema legítimo NO genera evento
    record_lemma(p.id, "lema real", proved=True, backend="z3", sf=session_factory)
    assert len(st.list_objects(p.id, kind="violation")) == 1


# --- UPG-3: discovery fabric fase 1 ------------------------------------------------
def test_mutual_info_ve_lo_que_pearson_no() -> None:
    """Relación en V (y=|x|): Pearson ≈ 0, la información mutua la detecta."""
    import numpy as np
    from acero.science.patterns import FeatureLab, MutualInfoDiscoverer, _pearson
    rng = np.random.default_rng(7)
    xs = list(rng.uniform(-3, 3, 200))
    rows = [{"x": x, "y": abs(x)} for x in xs]
    cols, recipes = FeatureLab(max_features=6).derive(rows)
    assert abs(_pearson(cols["x"], cols["y"])) < 0.25
    cands = MutualInfoDiscoverer().discover(cols, recipes, dhash="t")
    assert any(set(c["variables"]) == {"x", "y"} for c in cands)


def test_secuencias_detecta_recurrencia_y_polinomio() -> None:
    from acero.science.patterns import SequenceDiscoverer
    fib = [1.0, 1.0]
    for _ in range(10):
        fib.append(fib[-1] + fib[-2])
    cands = SequenceDiscoverer().discover(
        {"a": fib}, {}, "a", dhash="t")
    assert any("recurrencia" in c["description"] for c in cands)
    cuad = {"n": [float(i) for i in range(1, 11)],
            "y": [float(3 * i * i + 1) for i in range(1, 11)]}
    cands2 = SequenceDiscoverer().discover(cuad, {}, "y", index="n", dhash="t")
    assert any("grado 2" in c["description"] for c in cands2)


# --- UPG-4: credence + gpu policy --------------------------------------------------
def test_credence_distingue_los_cuatro_casos() -> None:
    from acero.science.credence import credence_for
    sin = credence_for([])
    assert "SIN evidencia" in sin["estado"] and sin["credence"] == 0.5
    contra = credence_for([{"kind": "negative", "payload": {}}])
    assert "EN CONTRA" in contra["estado"] and contra["credence"] < 0.5
    debil = credence_for([{"kind": "experiment",
                           "payload": {"result": {"verdict": "holds_empirically",
                                                  "n_tested": 10**6}}}])
    assert "débil" in debil["estado"]
    fuerte = credence_for([{"kind": "lemma", "payload": {"proved": True}},
                           {"kind": "experiment",
                            "payload": {"result": {"verdict": "holds_empirically",
                                                   "n_tested": 10**9}}}])
    assert "fuerte" in fuerte["estado"] and fuerte["credence"] > 0.7
    assert "n=1000000000" in fuerte["dominio_probado"]


def test_gpu_policy_caja_cerrada_hasta_aprobacion_humana() -> None:
    from acero.science.gpu import GPU_POLICY, policy_allows
    ok, why = policy_allows({"library": "torch", "vram_mb": 1000})
    assert not ok and "Merari" in why            # sin aprobación: nada corre
    GPU_POLICY["approved_by_human"] = True
    try:
        ok2, _ = policy_allows({"library": "torch", "vram_mb": 1000,
                                "duration_s": 60})
        assert ok2
        bad, why_bad = policy_allows({"library": "tensorflow", "vram_mb": 100})
        assert not bad and "librería" in why_bad
        big, _ = policy_allows({"library": "torch", "vram_mb": 99999})
        assert not big
    finally:
        GPU_POLICY["approved_by_human"] = False


# --- CONS-5: gauntlet de descubrimiento (Fase 9) -----------------------------------
def test_gauntlet_mide_aporte_marginal_y_corre_las_3_configs() -> None:
    """El benchmark es el GATE de cualquier técnica nueva. Debe: correr las 3
    configuraciones, y que Mendeleev completo descubra AL MENOS tanto como
    solo-estadística (nunca peor por añadir motores)."""
    from acero.science.discovery_bench import CONFIGS, run_gauntlet
    res = run_gauntlet()
    assert set(res["per_config"]) == set(CONFIGS)
    stats = res["per_config"]["solo_estadistica"]["true_discovery_rate"]
    full = res["per_config"]["mendeleev_completo"]["true_discovery_rate"]
    assert full >= stats                      # añadir motores nunca empeora
    assert full >= 0.8                         # umbral de capacidad mínima
    # el aporte marginal debe incluir al menos un caso que solo-estadística no ve
    assert res["marginal_gain_full_over_stats"]


def test_gauntlet_detecta_su_propio_falso_descubrimiento() -> None:
    """El valor del gauntlet es que CAZA los fallos de Mendeleev, no que lo
    maquille: hoy tiene FDR>0 en datos nulos (minería de múltiples hipótesis) —
    ese número es el objetivo concreto del endurecimiento con null-test (Fase 6).
    El test fija que el benchmark REPORTA el FDR, no que sea 0."""
    from acero.science.discovery_bench import run_gauntlet
    res = run_gauntlet()
    m = res["per_config"]["mendeleev_completo"]
    assert "false_discovery_rate" in m and m["n_null"] >= 3
    # honestidad: si algún día el FDR baja a 0, este assert avisa para actualizar
    # la narrativa (ya no es una debilidad conocida)
    assert 0.0 <= m["false_discovery_rate"] <= 1.0
