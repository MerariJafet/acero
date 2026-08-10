"""Tests del director dinámico: Bohr decide, repite, reinicia y cierra HONESTO."""
from __future__ import annotations

from acero.science.bohr import (ACTION_MENU, HONEST_DISPOSITIONS, BohrOrchestrator,
                                build_knowledge)


def _d(action: str, **kw) -> dict:
    base = {"action": action, "reason": f"probar {action}", "expected": "info",
            "statement": "", "frontier": "", "why_stuck": "", "idea": "",
            "piezas": [], "budget_min": 0, "disposition": ""}
    base.update(kw)
    return base


class _ScriptedProvider:
    """Devuelve decisiones guionizadas en orden; registra los prompts que vio."""

    def __init__(self, decisions: list[dict]) -> None:
        self._ds = list(decisions)
        self.prompts: list[str] = []

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0
                      ) -> dict:
        self.prompts.append(prompt)
        return self._ds.pop(0) if self._ds else _d("cerrar",
                                                   disposition="needs_human_review")


def test_bohr_dirige_repite_y_cierra_honesto() -> None:
    calls: list[str] = []

    def ex(name):
        def _run(statement, decision):
            calls.append(name)
            return {"summary": f"{name} ok sobre: {statement[:30]}",
                    "verdict": "holds_empirically" if name == "popper" else ""}
        return _run

    prov = _ScriptedProvider([
        _d("hipatia"), _d("popper"),
        _d("aristoteles"),                          # segunda opinión adversarial
        _d("popper"),                               # repite con otro ángulo
        _d("cerrar", disposition="holds_empirically",
           reason="sobrevivió dos ataques y la crítica"),
    ])
    orch = BohrOrchestrator(prov, {k: ex(k) for k in
                                   ("hipatia", "popper", "aristoteles")},
                            knowledge="K", max_actions=10)
    out = orch.run("toda suma de dos pares es par")
    assert out["disposition"] == "holds_empirically"
    assert calls == ["hipatia", "popper", "aristoteles", "popper"]
    assert "MENÚ DE JUGADAS" in prov.prompts[0]      # Bohr ve el menú completo
    assert "HISTORIAL" in prov.prompts[-1]           # y el estado real acumulado


def test_bohr_reinicia_con_enunciado_nuevo() -> None:
    seen: list[str] = []

    def ex(statement, decision):
        seen.append(statement)
        return {"summary": "ok"}

    prov = _ScriptedProvider([
        _d("popper"),
        _d("reiniciar", statement="version REFORMULADA de la conjetura"),
        _d("popper"),
        _d("cerrar", disposition="partial_progress", reason="lema parcial"),
    ])
    out = BohrOrchestrator(prov, {"popper": ex}, max_actions=10).run("original")
    assert seen == ["original", "version REFORMULADA de la conjetura"]
    assert out["statement"] == "version REFORMULADA de la conjetura"
    assert out["disposition"] == "partial_progress"


def test_disposicion_deshonesta_se_degrada() -> None:
    prov = _ScriptedProvider([_d("cerrar", disposition="solved",
                                 reason="¡lo resolví!")])
    out = BohrOrchestrator(prov, {}).run("problema abierto famoso")
    assert out["disposition"] == "needs_human_review"   # anti-Erdősgate en código


def test_accion_invalida_se_reintenta_y_luego_cierra() -> None:
    prov = _ScriptedProvider([_d("einstein"), _d("newton"), _d("tesla")])
    out = BohrOrchestrator(prov, {}).run("x")
    assert out["disposition"] == "needs_human_review"
    assert "no está en el menú" in prov.prompts[1]      # el error se le muestra


def test_guard_anti_bucle_bloquea_la_cuarta_repeticion_identica() -> None:
    prov = _ScriptedProvider([_d("popper")] * 4
                             + [_d("cerrar", disposition="needs_human_review",
                                   reason="fin")])
    runs: list[int] = []

    def ex(statement, decision):
        runs.append(1)
        return {"summary": "IDENTICO siempre"}

    out = BohrOrchestrator(prov, {"popper": ex}, max_actions=10).run("x")
    assert len(runs) == 3                                # la 4ª quedó bloqueada
    assert any("anti-bucle" in str(h.get("summary")) for h in out["history"])


def test_ejecutor_roto_no_mata_el_ciclo() -> None:
    def boom(statement, decision):
        raise RuntimeError("kaputt")

    prov = _ScriptedProvider([_d("turing"),
                              _d("cerrar", disposition="dropped", reason="sin vía")])
    out = BohrOrchestrator(prov, {"turing": boom}).run("x")
    assert out["disposition"] == "dropped"
    assert "kaputt" in str(out["history"][0]["summary"])


def test_conocimiento_incluye_a_los_16_y_el_toolbox() -> None:
    k = build_knowledge()
    for nombre in ("Ramanujan", "Turing", "Hipatia", "Bohr"):
        assert nombre in k
    assert "PIEZAS" in k and "sympy" in k
    assert set(ACTION_MENU) >= {"hipatia", "popper", "ramanujan", "turing",
                                "reiniciar", "cerrar"}
    assert "needs_human_review" in HONEST_DISPOSITIONS


def test_run_bohr_cycle_registra_todo_en_el_ledger(session_factory) -> None:
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.investigator_bridge import run_bohr_cycle

    class _Orch:
        def run(self, claim):
            return {"disposition": "partial_progress", "close_reason": "lema",
                    "statement": claim, "history": [
                        {"action": "popper", "reason": "atacar",
                         "summary": "aguantó"}],
                    "n_actions": 1, "elapsed_s": 0.1}

    lg = ResearchLedger(session_factory)
    p = lg.create_project("Bohr dinámico", domain="matemáticas")
    out = run_bohr_cycle(p.id, "conjetura X", orchestrator=_Orch(),
                         sf=session_factory)
    assert out["disposition"] == "partial_progress"
    store = DiscoveryStore(session_factory, lg)
    reps = store.list_objects(p.id, kind="report")
    assert reps and reps[-1]["origin"] == "consejo-dinamico"
    assert "Bitácora" in reps[-1]["markdown"]


def test_run_bohr_cycle_conecta_ramanujan_turing_noether_al_dashboard(
        session_factory) -> None:
    """Regresión del bug reportado por Merari (2026-08-10): las chispas/builds/
    arbitrajes existían en el ledger pero NO se enlazaban a la hipótesis
    (faltaba parent_id) ni sumaban progreso a su personaje — el dashboard los
    mostraba en 0%/idle pese a tener fichas reales. Este test falla si vuelve
    a pasar."""
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.portal.council import build_flows, council_for
    from acero.portal.investigator_bridge import run_bohr_cycle

    decisions = iter([
        _d("ramanujan", frontier="frontera de prueba", why_stuck="agotado"),
        _d("turing"),
        _d("noether"),
        _d("cerrar", disposition="needs_human_review", reason="fin de prueba"),
    ])

    class _FakeProvider:
        def complete_json(self, prompt, schema, *, temperature=0.0):
            props = schema.get("properties", {})
            if "action" in props:
                return next(decisions)
            if "ideas" in props:
                return {"ideas": [{"chispa": "¿y si sí?", "analogia": "a",
                                   "plan": "p", "piezas": ["sympy"],
                                   "piezas_faltantes": [], "probabilidad": 0.4,
                                   "primer_experimento": "e"}]}
            if "code" in props:
                return {"razonamiento": "r", "necesita_piezas": [],
                        "code": "print('VEREDICTO: ok')", "criterio_exito": "v"}
            if "veredicto" in props:
                return {"veredicto": "prometedor", "resumen": "va bien",
                        "fortalezas": [], "objeciones_mayores": [],
                        "objeciones_menores": [], "literatura_faltante": [],
                        "chequeos_sugeridos": [], "dictamen_novedad": "n/a"}
            raise AssertionError(f"esquema inesperado: {list(props)}")

    lg = ResearchLedger(session_factory)
    p = lg.create_project("Bug del dashboard", domain="matemáticas")
    out = run_bohr_cycle(p.id, "conjetura de prueba", provider=_FakeProvider(),
                         sf=session_factory)
    assert out["disposition"] == "needs_human_review"

    store = DiscoveryStore(session_factory, lg)
    rows = store.list_rows(p.id)
    hid = next(r["id"] for r in rows if r["kind"] == "candidate")
    sparks = [r for r in rows if r["kind"] == "spark"]
    builds = [r for r in rows if r["kind"] == "build"]
    reviews = [r for r in rows if r["kind"] == "review"]
    assert sparks and all(r["parent_id"] == hid for r in sparks)
    assert builds and all(r["parent_id"] == hid for r in builds)
    assert reviews and all(r["parent_id"] == hid for r in reviews)

    items = {k: [r["payload"] for r in rows if r["kind"] == k]
             for k in ("spark", "build", "review")}
    flows = build_flows(rows)
    data = council_for({}, items=items, flows=flows)
    by_id = {pr["id"]: pr for pr in data["personas"]}
    for persona_id in ("ramanujan", "turing", "noether"):
        assert by_id[persona_id]["progress"] > 0, (
            f"{persona_id} sigue en 0% pese a tener fichas reales")
        assert by_id[persona_id]["source"] == "project"
    kinds_in_rail = {s["kind"] for s in flows[0]["steps"]}
    assert {"spark", "build", "review"} <= kinds_in_rail
