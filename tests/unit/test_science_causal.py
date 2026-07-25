"""CCC-4: causal DAG, back-door criterion, identifiability gate (offline)."""

from __future__ import annotations

from acero.science.causal import CausalGraph, Estimand, audit


def _confounded():
    # C confounds X→Y:  X ← C → Y,  X → Y
    g = CausalGraph()
    g.add_edge("C", "X"); g.add_edge("C", "Y"); g.add_edge("X", "Y")
    return g


def test_confounder_needs_adjustment():
    g = _confounded()
    ok0, _ = g.satisfies_backdoor("X", "Y", set())
    okC, _ = g.satisfies_backdoor("X", "Y", {"C"})
    assert not ok0            # unadjusted → backdoor path X←C→Y open
    assert okC                # adjusting for C blocks it


def test_audit_blocks_causal_language_when_unidentifiable():
    g = _confounded()
    est = Estimand("X", "Y", "individuo", "poblacion", adjustment_set=())
    v = audit(est, g)
    assert not v.identifiable and not v.allows_causal_language
    est2 = Estimand("X", "Y", "individuo", "poblacion", adjustment_set=("C",))
    v2 = audit(est2, g)
    assert v2.identifiable and v2.allows_causal_language


def test_conditioning_on_collider_opens_bias():
    # X → K ← Y  (K is a collider); X → Y is the causal effect
    g = CausalGraph()
    g.add_edge("X", "K"); g.add_edge("Y", "K"); g.add_edge("X", "Y")
    est_clean = Estimand("X", "Y", "u", "p", adjustment_set=())
    assert audit(est_clean, g).identifiable            # empty set identifies
    est_bad = Estimand("X", "Y", "u", "p", adjustment_set=("K",), colliders=("K",))
    v = audit(est_bad, g)
    assert not v.identifiable and "K" in v.opened_colliders


def test_adjusting_for_mediator_is_flagged():
    # X → M → Y : M is a mediator; adjusting for it over-controls
    g = CausalGraph()
    g.add_edge("X", "M"); g.add_edge("M", "Y")
    est = Estimand("X", "Y", "u", "p", adjustment_set=("M",), mediators=("M",))
    v = audit(est, g)
    assert not v.identifiable and "M" in v.conditioned_mediators


def test_cycle_is_rejected():
    g = CausalGraph()
    g.add_edge("A", "B"); g.add_edge("B", "A")
    assert g.has_cycle()
    v = audit(Estimand("A", "B", "u", "p"), g)
    assert not v.identifiable and "ciclo" in v.reason


def test_descendants_and_backdoor_paths():
    g = _confounded()
    assert g.descendants("C") == {"X", "Y"}
    bp = g.backdoor_paths("X", "Y")
    assert ["X", "C", "Y"] in bp            # the confounding path
