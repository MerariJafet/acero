"""El puente investigador → ledger: el trabajo del Consejo se escribe al proyecto."""

from __future__ import annotations

from acero.discovery.store import DiscoveryStore
from acero.ledger.service import ResearchLedger
from acero.portal.investigator_bridge import (
    record_hypothesis, record_result, run_council)


class _FakeLoop:
    """A ResearchLoop stand-in returning a canned ambitious result."""

    def __init__(self, result):
        self._r = result

    def investigate(self, claim, **kw):
        return self._r


def test_records_hypothesis_and_experiment_with_verdict(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Lehmer", domain="teoría de números")
    out = record_result(
        p.id, "No existe compuesto n con phi(n) | n-1",
        {"verdict": "holds_empirically", "detail": "sin contraejemplo en 2.5M",
         "computational": {"n_tested": 2540152, "counterexample": None}},
        persona="popper", sf=session_factory)
    assert out["verdict"] == "holds_empirically"

    store = DiscoveryStore(session_factory, lg)
    hyps = store.list_objects(p.id, kind="candidate")
    exps = store.list_objects(p.id, kind="experiment")
    assert len(hyps) == 1                       # dashboard cuenta +1 hipótesis
    assert len(exps) == 1                       # +1 experimento con su veredicto
    assert (exps[0].get("result") or {}).get("verdict") == "holds_empirically"


def test_refutation_also_writes_a_negative(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("cs", domain="math")
    record_result(p.id, "conjetura falsa",
                  {"verdict": "refuted",
                   "computational": {"counterexample": {"n": 6}, "n_tested": 100}},
                  persona="popper", sf=session_factory)
    store = DiscoveryStore(session_factory, lg)
    assert len(store.list_objects(p.id, kind="negative")) == 1   # contraejemplo registrado


def test_record_hypothesis_alone(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("h", domain="math")
    hid = record_hypothesis(p.id, "una conjetura", persona="hilbert", sf=session_factory)
    assert hid
    hyps = DiscoveryStore(session_factory, lg).list_objects(p.id, kind="candidate")
    assert len(hyps) == 1
    # la tarjeta del dashboard lee tag/title — sin esto salía 'H?:' vacía
    assert hyps[0]["tag"] == "H1"
    assert hyps[0]["title"] == "una conjetura"


def test_record_hypothesis_dedups_same_live_claim(session_factory):
    """Relanzar el ciclo sobre la MISMA conjetura NO crea H1..Hn idénticas: reutiliza
    la hipótesis viva y le cuelga el trabajo nuevo."""
    lg = ResearchLedger(session_factory)
    p = lg.create_project("dedup", domain="math")
    a = record_hypothesis(p.id, "misma conjetura de decoherencia", sf=session_factory)
    b = record_hypothesis(p.id, "  Misma   CONJETURA de decoherencia ", sf=session_factory)
    assert a == b                                    # misma H, no duplicado
    c = record_hypothesis(p.id, "otra conjetura distinta", sf=session_factory)
    assert c != a
    assert len(DiscoveryStore(session_factory, lg)
               .list_objects(p.id, kind="candidate")) == 2


def test_run_council_records_ambitious_work_per_persona(session_factory):
    """U3: Bohr corre el ciclo y cada personaje deja su ficha real — incluida la
    contribución PARCIAL (condición necesaria verificada) sin declarar resuelto nada."""
    lg = ResearchLedger(session_factory)
    p = lg.create_project("problema abierto", domain="teoría de números")
    result = {
        "original": "C", "final_statement": "C (excluyendo n=1)",
        "disposition": "partial_progress", "final_verdict": "holds_empirically",
        "sketch": "boceto honesto", "lemma": "lema núcleo de la reducción",
        "formal_support": {"result": "proved"},
        "contributions": [{"kind": "necessary_condition",
                           "statement": "todo contraejemplo n es par",
                           "why_partial": "acota dónde buscar; no resuelve el problema",
                           "proved": True, "backend": "z3"}],
        "trail": [{"depth": 1, "statement": "C", "observation": None},
                  {"depth": 2, "statement": "C (excluyendo n=1)",
                   "observation": "excluye el borde trivial"}],
    }
    fake_novelty = lambda c: {  # noqa: E731 - Hipatia inyectada (multi-fuente simulada)
        "verdict": "likely_open", "rationale": "no hay resolver directo",
        "recommendation": "atacar computacionalmente",
        "resolving_papers": [],
        "hits": [{"title": "A survey of C-like conjectures", "year": 2021,
                  "doi": "10.1/x", "source": "arxiv"}]}
    def fake_critic(pid, hid, ctx):
        # Aristóteles inyectado: persiste su crítica como el real
        DiscoveryStore(session_factory, lg).put(
            pid, "critique", "crit_test1",
            {"target_id": hid, "verdict": "prometedor", "summary": "objeción menor"},
            status="ISSUED", actor="critic_agent", summary="crítica: prometedor")
        return {"verdict": "prometedor"}

    fake_anomalies = lambda pid: {"ok": True, "created": [{"tag": "H9"}]}  # noqa: E731
    out = run_council(p.id, "C", sf=session_factory, loop=_FakeLoop(result),
                      novelty=fake_novelty, critic=fake_critic,
                      anomalies=fake_anomalies,
                      narrator=lambda facts: "NARRATIVA DE PRUEBA: qué hicimos y qué "
                                             "significa, en lenguaje humano.")
    assert out["disposition"] == "partial_progress"          # honesto: NO 'verified'
    store = DiscoveryStore(session_factory, lg)
    assert len(store.list_objects(p.id, kind="candidate")) == 1     # Hilbert
    assert len(store.list_objects(p.id, kind="experiment")) == 1    # Popper
    refs = store.list_objects(p.id, kind="reformulation")           # Feynman
    lems = store.list_objects(p.id, kind="lemma")                   # Gödel/Euclides
    assert len(refs) == 1 and refs[0]["statement"].startswith("C (excluyendo")
    assert len(lems) >= 1 and any(l.get("proved") for l in lems)    # contribución probada
    # U5: el ciclo de Bohr ahora ES el flujo completo — Hipatia y Gauss incluidos
    lits = store.list_objects(p.id, kind="literature")              # Hipatia
    assert len(lits) == 1 and lits[0]["title"].startswith("A survey")
    assert out["novelty"] == "likely_open"
    assert out["dossier"] is True                                    # Gauss empaquetó
    assert len(store.list_objects(p.id, kind="dossier")) == 1        # espera revisión humana
    # Bohr ORQUESTA: sus decisiones (a quién y POR QUÉ) quedan en el ledger
    decs = store.list_objects(p.id, kind="decision")
    tos = {d.get("to") for d in decs}
    assert "hipatia" in tos and "gauss" in tos                       # asignaciones con porqué
    assert "aristoteles" in tos and "kepler" in tos                  # crítica + anomalías AUTO
    assert all(d.get("reason") for d in decs)
    # U6: Aristóteles automático + Kepler anomalías + BITÁCORA tipo paper
    assert out["critic"] == "prometedor"
    assert out["anomalies"] == 1
    assert len(store.list_objects(p.id, kind="critique")) == 1
    reps = store.list_objects(p.id, kind="report")
    assert len(reps) == 1 and out["report"] is True
    md = reps[0]["markdown"]
    for section in ("Conjetura investigada", "Novedad (Hipatia)", "iteraciones",
                    "Crítica (Aristóteles)", "Anomalías (Kepler)",
                    "¿Publicación o estudio?", "Recomendación de Bohr"):
        assert section in md                                          # informe completo
    assert "revisión humana" in md                                    # techo epistémico
    # narrativa en lenguaje humano + resumen en cristiano + datos como apéndice
    assert "Informe narrativo" in md and "NARRATIVA DE PRUEBA" in md
    assert "Resumen ejecutivo (en cristiano)" in md
    assert "APÉNDICE" in md
