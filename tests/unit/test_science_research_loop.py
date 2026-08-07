"""Offline tests for ResearchLoop + the HumanAttitude creative filter."""

from __future__ import annotations

from acero.science.explorer_ledger import ExplorerLedger
from acero.science.research_loop import HumanAttitude, ResearchLoop


def _led():
    return ExplorerLedger(store=None)


class _AttProv:
    """Stub provider driving HumanAttitude via complete_json."""
    def __init__(self, out):
        self._out = out

    def available(self):
        return True

    def complete_json(self, prompt, schema, temperature=0.0):
        return self._out(prompt) if callable(self._out) else self._out

    class _R:
        text = "boceto de prueba: inducción sobre n…"

    def complete(self, prompt, temperature=0.0, max_tokens=0):
        return self._R()


def test_human_attitude_defaults_to_escalate_without_provider():
    a = HumanAttitude(provider=None)

    class _Down:
        def available(self):
            return False
    a._provider = _Down()
    r = a.observe("algo", {"verdict": "holds_empirically"}, [])
    assert r["next_action"] == "escalate_to_human"


def test_human_attitude_sanitizes_bad_action():
    prov = _AttProv({"observation": "x", "verdict_is_trivial": False,
                     "refined_statement": "", "alternative_angles": [],
                     "next_action": "nonsense"})
    r = HumanAttitude(provider=prov).observe("c", {"verdict": "refuted"}, [])
    assert r["next_action"] == "escalate_to_human"


def test_second_move_refines_a_trivial_boundary_refutation():
    """The star behavior: refuted at n=1 (trivial) → exclude the edge, re-attack the core."""
    def prober(stmt):
        if "n >= 2" in stmt:
            return {"verdict": "holds_empirically", "n_tested": 5000, "counterexample": None}
        return {"verdict": "refuted", "counterexample": {"n": 1}, "n_tested": 80}

    def attitude(stmt, probe, trail):
        if probe["verdict"] == "refuted":
            return {"observation": "falla trivial en n=1", "verdict_is_trivial": True,
                    "refined_statement": stmt + " (para n >= 2)",
                    "alternative_angles": ["excluir el borde"],
                    "next_action": "refine_and_retry"}
        return {"observation": "sobrevive", "verdict_is_trivial": False,
                "refined_statement": "", "alternative_angles": [],
                "next_action": "escalate_to_human"}

    loop = ResearchLoop(prober=prober, attitude=attitude, ledger=_led())
    r = loop.investigate("conjetura P(n)", max_depth=3)
    assert r["disposition"] == "needs_human_review"     # survived after refining
    assert len(r["trail"]) == 2
    assert r["trail"][0]["trivial"] is True
    assert "n >= 2" in r["final_statement"]              # sharpened core, not the trivial form


def test_nontrivial_refutation_stops_as_refuted():
    loop = ResearchLoop(
        prober=lambda s: {"verdict": "refuted", "counterexample": {"n": 42}, "n_tested": 99},
        attitude=lambda s, p, t: {"observation": "contraejemplo real", "verdict_is_trivial": False,
                                  "refined_statement": "", "alternative_angles": [],
                                  "next_action": "drop"},
        ledger=_led())
    r = loop.investigate("conjetura falsa", max_depth=3)
    assert r["disposition"] == "refuted"


def test_attempt_proof_via_explorer_can_verify_a_survivor():
    class _Explorer:
        def explore(self, goal, approaches=3, rounds=1):
            return {"verdict": "verified", "verdict_detail": "demostrado", "why": "porque sí"}

    loop = ResearchLoop(
        prober=lambda s: {"verdict": "holds_empirically", "n_tested": 10000, "counterexample": None},
        attitude=lambda s, p, t: {"observation": "hay estructura", "verdict_is_trivial": False,
                                  "refined_statement": "", "alternative_angles": [],
                                  "next_action": "attempt_proof"},
        explorer=_Explorer(), ledger=_led())
    r = loop.investigate("conjetura demostrable", max_depth=2)
    assert r["disposition"] == "verified"


def test_formally_supported_when_core_lemma_is_proved():
    """Closing the loop: the sketch reduces to a lemma sympy PROVES → formally_supported
    (never full 'verified' — the reduction bridge still needs a human)."""
    class _FProv:
        def available(self):
            return True

        def complete_json(self, prompt, schema, temperature=0.0):
            # the FORMALIZER returns a provable identity as the core lemma
            return {"lemma": "identidad núcleo", "reduction": "prueba esto y cierra",
                    "formal_claim": {"kind": "identity", "lhs": "sin(x)**2+cos(x)**2",
                                     "rhs": "1", "expr": "", "var": "", "to": "",
                                     "expected": "", "term": "", "index": "", "lower": "",
                                     "upper": "", "closed": ""}}

        class _R:
            text = "boceto"

        def complete(self, prompt, temperature=0.0, max_tokens=0):
            return self._R()

    loop = ResearchLoop(
        provider=_FProv(),
        prober=lambda s: {"verdict": "holds_empirically", "n_tested": 9000, "counterexample": None},
        attitude=lambda s, p, t: {"observation": "reduce a una identidad",
                                  "verdict_is_trivial": False, "refined_statement": "",
                                  "alternative_angles": [], "next_action": "attempt_proof"},
        ledger=_led())            # no explorer → goes to formalize path
    r = loop.investigate("conjetura reducible", max_depth=1)
    assert r["disposition"] == "formally_supported"
    assert r["formal_support"]["result"] == "proved"
    assert r["lemma"] == "identidad núcleo"


def test_formally_supported_via_godel_z3_backend():
    """Automatic flow routes a COUNTING/logic lemma to Gödel (Z3), not sympy."""
    import pytest
    pytest.importorskip("z3")

    class _FZProv:
        def available(self):
            return True

        def complete_json(self, prompt, schema, temperature=0.0):
            return {"lemma": "núcleo de conteo", "reduction": "cierra el argumento",
                    "formal_claim": {"kind": ""},                       # sympy no aplica
                    "z3_claim": {"kind": "int_forall", "expr": "n*n >= 0",
                                 "vars": ["n"], "assume": [], "sort": "int"}}

        class _R:
            text = "boceto"

        def complete(self, prompt, temperature=0.0, max_tokens=0):
            return self._R()

    loop = ResearchLoop(
        provider=_FZProv(),
        prober=lambda s: {"verdict": "holds_empirically", "n_tested": 9000,
                          "counterexample": None},
        attitude=lambda s, p, t: {"observation": "reduce a conteo",
                                  "verdict_is_trivial": False, "refined_statement": "",
                                  "alternative_angles": [], "next_action": "attempt_proof"},
        ledger=_led())
    r = loop.investigate("conjetura de conteo", max_depth=1)
    assert r["disposition"] == "formally_supported"
    proof = [t for t in r["trail"] if t.get("depth") == "proof"][0]
    assert proof["backend"] == "z3"           # closed by Gödel, not Euclides


def test_formalize_failure_still_escalates():
    class _FProv:
        def available(self):
            return True

        def complete_json(self, prompt, schema, temperature=0.0):
            return {"lemma": "", "reduction": "", "formal_claim": {"kind": ""}}  # nada reducible

        class _R:
            text = "boceto honesto"

        def complete(self, prompt, temperature=0.0, max_tokens=0):
            return self._R()

    loop = ResearchLoop(
        provider=_FProv(),
        prober=lambda s: {"verdict": "holds_empirically", "n_tested": 9000, "counterexample": None},
        attitude=lambda s, p, t: {"observation": "no reduce", "verdict_is_trivial": False,
                                  "refined_statement": "", "alternative_angles": [],
                                  "next_action": "attempt_proof"},
        ledger=_led())
    r = loop.investigate("conjetura no reducible", max_depth=1)
    assert r["disposition"] == "needs_human_review"


def test_survivor_escalates_with_a_sketch():
    prov = _AttProv({"observation": "s", "verdict_is_trivial": False, "refined_statement": "",
                     "alternative_angles": [], "next_action": "escalate_to_human"})
    loop = ResearchLoop(provider=prov,
                        prober=lambda s: {"verdict": "holds_empirically", "n_tested": 1000,
                                          "counterexample": None},
                        ledger=_led())
    r = loop.investigate("conjetura fuerte", max_depth=1)
    assert r["disposition"] == "needs_human_review"
    assert r["sketch"]                                   # produced a proof sketch to hand off
