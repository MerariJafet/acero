"""Tests offline de TOOLBOX (catálogo LEGO), Ramanujan (chispa) y Turing (constructor)."""
from __future__ import annotations

from acero.science import toolbox
from acero.science.spark import SparkEngine
from acero.science.turing import TuringBuilder


class _FakeProvider:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self.prompts: list[str] = []

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0
                      ) -> dict:
        self.prompts.append(prompt)
        return self._payloads.pop(0)


def test_toolbox_inventory_declara_niveles_y_capacidades() -> None:
    inv = toolbox.inventory()
    names = {t["name"] for t in inv["available"]} | {t["name"] for t in inv["missing"]}
    assert {"sympy", "z3", "sage", "frontier_toolkit", "novelty_check"} <= names
    for t in inv["available"]:
        assert t["nivel"] and t["capacidades"]


def test_catalog_text_sirve_para_prompts() -> None:
    txt = toolbox.catalog_text()
    assert "PIEZAS DISPONIBLES" in txt and "sympy" in txt


def test_spark_ordena_por_probabilidad_y_ancla_al_catalogo() -> None:
    ideas = [
        {"chispa": "¿y si lo vemos como matrices?", "analogia": "álgebra lineal",
         "plan": "p", "piezas": ["numpy"], "piezas_faltantes": [],
         "probabilidad": 0.2, "primer_experimento": "e"},
        {"chispa": "¿y si usamos curvas elípticas?", "analogia": "aritmética",
         "plan": "p", "piezas": ["cypari2"], "piezas_faltantes": ["sage"],
         "probabilidad": 0.6, "primer_experimento": "e"},
        {"chispa": "idea con probabilidad rota", "analogia": "x", "plan": "p",
         "piezas": [], "piezas_faltantes": [], "probabilidad": 7,
         "primer_experimento": "e"},
    ]
    prov = _FakeProvider([{"ideas": ideas}])
    out = SparkEngine(prov).ignite("frontera X", "no alcanza sympy", n_ideas=3)
    assert out[0]["probabilidad"] == 1.0            # 7 → recortada a 1.0 (saneo)
    assert out[1]["chispa"].startswith("¿y si usamos curvas")
    assert "CATÁLOGO DE PIEZAS" in prov.prompts[0]  # la chispa ve el LEGO real
    assert "FRONTERA" in prov.prompts[0]


def test_turing_repara_y_declara_veredicto() -> None:
    plan_malo = {"razonamiento": "intento 1", "necesita_piezas": ["gmpy2"],
                 "code": "explota", "criterio_exito": "VEREDICTO"}
    plan_bueno = {"razonamiento": "intento 2", "necesita_piezas": [],
                  "code": "ok", "criterio_exito": "VEREDICTO"}
    prov = _FakeProvider([plan_malo, plan_bueno])
    runs = {"explota": {"rc": 1, "stdout": "", "stderr": "SyntaxError"},
            "ok": {"rc": 0, "stdout": "EVIDENCIA: 42\nVEREDICTO: señal real",
                   "stderr": ""}}
    ensured: list[str] = []
    tb = TuringBuilder(prov, run_fn=lambda code, t: runs[code],
                       ensure_fn=lambda p: (ensured.append(p) or
                                            {"ok": True, "detail": "ya estaba"}))
    out = tb.build_and_run({"chispa": "c", "plan": "p", "primer_experimento": "e"},
                           ["sympy"], budget_s=60, round_timeout_s=10)
    assert out["status"] == "completed"
    assert out["verdict"] == "VEREDICTO: señal real"
    assert out["evidence"] == ["EVIDENCIA: 42"]
    assert len(out["rounds"]) == 2                  # falló y reparó
    assert ensured == ["gmpy2"]                     # pidió la pieza al TOOLBOX
    assert "FALLO ANTERIOR" in prov.prompts[1]      # la reparación vio el error


def test_turing_respeta_presupuesto() -> None:
    prov = _FakeProvider([{"razonamiento": "r", "necesita_piezas": [],
                           "code": "x", "criterio_exito": "v"}] * 50)
    tb = TuringBuilder(prov, run_fn=lambda c, t: {"rc": 1, "stdout": "",
                                                  "stderr": "err"},
                       ensure_fn=lambda p: {"ok": True, "detail": ""})
    out = tb.build_and_run({"chispa": "c"}, [], budget_s=0, round_timeout_s=5)
    assert out["status"] == "budget_exhausted" and out["rounds"] == []


# --- el flujo completo de la chispa escribe al ledger del proyecto ------------------
class _FakeSpark:
    def ignite(self, frontier, why, n_ideas=5):
        return [{"chispa": "¿y si usamos matrices de transferencia?",
                 "analogia": "mecánica estadística", "plan": "p",
                 "piezas": ["numpy", "sympy"], "piezas_faltantes": [],
                 "probabilidad": 0.4, "primer_experimento": "e"}]


class _FakeBuilder:
    def build_and_run(self, chispa, piezas, budget_s=0, round_timeout_s=0,
                      on_event=None):
        if on_event:
            on_event("ronda", {"razonamiento": "r", "rc": 0, "stdout": "", "stderr": ""})
        return {"status": "completed", "verdict": "VEREDICTO: patrón confirmado",
                "evidence": ["EVIDENCIA: traza"], "rounds": [{"code": "x=1"}],
                "elapsed_s": 1.2}


def test_run_spark_flow_registra_chispa_build_y_decisiones(session_factory):
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.investigator_bridge import run_spark_flow
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Frontera ES", domain="matemáticas")
    out = run_spark_flow(p.id, "cuadrados duros mod 840", "no hay familias polinomiales",
                         spark=_FakeSpark(), builder=_FakeBuilder(),
                         sf=session_factory)
    assert out["status"] == "completed"
    assert out["verdict"].startswith("VEREDICTO")
    store = DiscoveryStore(session_factory, lg)
    sparks = store.list_objects(p.id, kind="spark")
    builds = store.list_objects(p.id, kind="build")
    decs = store.list_objects(p.id, kind="decision")
    assert len(sparks) == 1 and sparks[0]["chispa"].startswith("¿y si")
    assert len(builds) == 1 and builds[0]["status"] == "completed"
    # Bohr decidió: → ramanujan, → turing, → godel (la evidencia pasa a prueba)
    tos = [d.get("to") for d in decs]
    assert "ramanujan" in tos and "turing" in tos and "godel" in tos


def test_personas_ramanujan_turing_en_el_consejo(session_factory):
    from acero.portal.council import KIND_PERSONA, OWNER_KIND, PERSONAS, _card
    ids = {p["id"] for p in PERSONAS}
    assert {"ramanujan", "turing"} <= ids
    assert OWNER_KIND["ramanujan"] == "spark" and OWNER_KIND["turing"] == "build"
    assert KIND_PERSONA["spark"] == "ramanujan" and KIND_PERSONA["build"] == "turing"
    c = _card("spark", {"chispa": "¿y si X?", "probabilidad": 0.3, "analogia": "a"})
    assert c["title"] == "¿y si X?" and c["verdict"] == "p=0.3"
    c2 = _card("build", {"idea": "i", "status": "completed",
                         "verdict": "VEREDICTO: señal"})
    assert c2["verdict"] == "completed" and "VEREDICTO" in c2["title"]
