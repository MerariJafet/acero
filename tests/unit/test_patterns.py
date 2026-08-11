"""Mendeleev: patrón ≠ descubrimiento, consenso pesado por independencia,
reproducibilidad desde el día uno."""

from __future__ import annotations

import math

from acero.science.patterns import (FeatureLab, StatisticalDiscoverer,
                                    SymbolicDiscoverer, consensus, dataset_hash,
                                    discover_all, make_candidate)


def _ley_cuadrada(n: int = 24) -> list[dict[str, float]]:
    # y = 3·x² con ruido diminuto — la ley debe SALTAR
    return [{"x": float(i), "y": 3.0 * i * i * (1 + 0.001 * ((i % 3) - 1))}
            for i in range(2, n + 2)]


def test_contrato_nunca_afirma_causalidad() -> None:
    c = make_candidate(method="statistical", variables=["a", "b"],
                       description="d", support=0.9, stability=0.8,
                       simplicity=0.7, provenance={"dataset_hash": "x"})
    assert c["causality"] == "NO_ESTABLECIDA"
    assert len(c["rival_hypotheses"]) == 4          # H1..H4 siempre presentes
    assert c["status"] == "CANDIDATE" and c["counterexamples"] == []
    assert c["provenance"]["dataset_hash"] == "x"


def test_dataset_hash_es_estable_y_sensible() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert dataset_hash(rows) == dataset_hash(list(rows))
    assert dataset_hash(rows) != dataset_hash(rows + [{"a": 5, "b": 6}])


def test_featurelab_deriva_con_receta_y_tope() -> None:
    rows = [{"p": float(i), "k": float(i * 2 + 1)} for i in range(1, 12)]
    cols, recipes = FeatureLab(max_features=20).derive(rows)
    assert len(cols) <= 20
    assert "log(p)" in cols and recipes["log(p)"] == "log(col('p'))"
    assert any("/" in name for name in cols)         # razones presentes
    # toda columna tiene receta → reproducible
    assert set(cols) == set(recipes)


def test_simbolico_encuentra_la_ley_de_potencia() -> None:
    rows = _ley_cuadrada()
    cands = discover_all(rows, target="y")
    leyes = [c for c in cands if c["method"] == "symbolic"]
    assert leyes, "debió encontrar y ≈ a·x^b"
    top = leyes[0]
    assert top["support_score"] > 0.99
    coef = top["provenance"]["coefficients"]
    assert abs(coef["b"] - 2.0) < 0.05               # exponente ≈ 2
    assert abs(coef["a"] - 3.0) < 0.3                # constante ≈ 3


def test_consenso_no_cuenta_cabezas_cuenta_vistas() -> None:
    """Dos métodos sobre la MISMA representación = una foto, no dos testigos."""
    a = make_candidate(method="statistical", variables=["x", "y"],
                       description="corr", support=0.95, stability=0.9,
                       simplicity=0.7, provenance={}, representation="cruda")
    b = make_candidate(method="symbolic", variables=["x", "y"],
                       description="ley", support=0.99, stability=0.9,
                       simplicity=0.8, provenance={}, representation="cruda")
    merged = consensus([a, b])
    assert len(merged) == 1
    assert merged[0]["methods_agree"] == ["statistical", "symbolic"]
    assert merged[0]["independent_views"] == 1        # ¡una sola vista!
    assert "NO independiente" in merged[0]["description"]


def test_consenso_vistas_distintas_si_suman() -> None:
    a = make_candidate(method="statistical", variables=["x", "y"],
                       description="corr", support=0.9, stability=0.9,
                       simplicity=0.7, provenance={}, representation="cruda")
    b = make_candidate(method="symbolic", variables=["x", "y"],
                       description="ley", support=0.95, stability=0.9,
                       simplicity=0.8, provenance={}, representation="log")
    merged = consensus([a, b])
    assert merged[0]["independent_views"] == 2


def test_pocos_datos_devuelve_vacio_no_inventa() -> None:
    assert discover_all([{"x": 1.0, "y": 2.0}, {"x": 2.0, "y": 4.0}]) == []


def test_estabilidad_no_medible_con_pocas_filas() -> None:
    """Con <5 filas la estabilidad es 0 (no medible), nunca inflada."""
    rows = [{"x": float(i), "y": float(3 * i)} for i in range(1, 5)]  # 4 filas
    cands = discover_all(rows, target="y")
    assert all(c["stability_score"] == 0.0 for c in cands)


def test_ejecutor_registra_patrones_en_el_ledger(session_factory) -> None:
    """Integración: Bohr juega 'mendeleev' → kind='pattern' con parent_id."""
    from acero.ledger.service import ResearchLedger
    from acero.portal.investigator_bridge import run_bohr_cycle

    p = ResearchLedger(session_factory).create_project("patrones", domain="math")

    class _Orch:
        def __init__(self, executors: dict) -> None:
            self._ex = executors

        def run(self, claim: str) -> dict:
            res = self._ex["mendeleev"](statement=claim, decision={
                "dataset_ref": "", "target": "y"})
            return {"disposition": "partial_progress", "close_reason": "test",
                    "statement": claim, "n_actions": 1, "elapsed_s": 0.1,
                    "history": [{"action": "mendeleev", "reason": "t",
                                 "summary": res["summary"]}]}

    class _Prov:
        def complete_json(self, prompt: str, schema: dict, *,
                          temperature: float = 0.0) -> dict:
            return {"hilos_no_explorados": [], "pista_pendiente": "",
                    "siguiente_claim": "", "razon": ""}

    # sembrar experimentos con métricas que siguen y = 3x²
    from acero.discovery.store import DiscoveryStore
    st = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    for i in range(2, 14):
        st.put(p.id, "experiment", f"exp_{i}",
               {"claim": "c", "result": {"metrics": {"x": i, "y": 3 * i * i}}},
               status="DONE", actor="Popper", summary="exp")

    # inyectar orquestador que juega mendeleev directamente (el puente importa
    # BohrOrchestrator desde science.bohr dentro de la función)
    import acero.science.bohr as bohr_mod
    orig = bohr_mod.BohrOrchestrator

    def _factory(provider, executors, **kw):  # noqa: ANN001
        return _Orch(executors)

    bohr_mod.BohrOrchestrator = _factory  # type: ignore[assignment]
    try:
        out = run_bohr_cycle(p.id, "buscar estructura", provider=_Prov(),
                             sf=session_factory)
    finally:
        bohr_mod.BohrOrchestrator = orig  # type: ignore[assignment]
    assert "patrones" in out["history"][0]["summary"]
    pats = st.list_objects(p.id, kind="pattern")
    assert pats, "los patrones deben quedar en el ledger"
    assert all(pt["causality"] == "NO_ESTABLECIDA" for pt in pats)
    rows_raw = st.list_rows(p.id)
    assert any(r.get("kind") == "pattern" and r.get("parent_id")
               for r in rows_raw), "parent_id enlaza el patrón a la hipótesis"
