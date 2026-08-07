"""El puente investigador → ledger: el trabajo del Consejo se escribe al proyecto."""

from __future__ import annotations

from acero.discovery.store import DiscoveryStore
from acero.ledger.service import ResearchLedger
from acero.portal.investigator_bridge import record_hypothesis, record_result


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
    assert len(DiscoveryStore(session_factory, lg).list_objects(p.id, kind="candidate")) == 1
