"""Sprint 11 tests: red team, scientific mutation, scorecard, readiness, publication."""

from __future__ import annotations

from acero.reliability.engine import build_card, run_reliability
from acero.reliability.mutation import run_mutation_testing
from acero.reliability.red_team import AttackOutcome, library, run_red_team
from acero.reliability.scorecard import (
    DIMENSION_NAMES,
    PublicationCandidate,
    ReadinessLevel,
    ScientificReliabilityCard,
)


def test_red_team_detects_every_attack():
    rep = run_red_team()
    assert not rep.missed, f"missed attacks: {rep.missed}"
    assert rep.detected == len(rep.results)


def test_red_team_covers_all_categories():
    cats = {c.category for c in library()}
    assert {"data", "statistics", "models", "literature", "human", "domain"} <= cats


def test_red_team_outcome_states_exist():
    assert AttackOutcome.MISSED and AttackOutcome.FALSE_POSITIVE and AttackOutcome.ABSTAINED


def test_scientific_mutations_all_caught():
    rep = run_mutation_testing()
    assert not rep.survived, f"survived mutations: {rep.survived}"


def test_no_discovery_confirmed_level():
    assert not any(lvl.name == "DISCOVERY_CONFIRMED" for lvl in ReadinessLevel)
    assert ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW in ReadinessLevel


def test_card_reports_dimensions_separately():
    card = build_card()
    d = card.as_dict()["dimensions"]
    assert set(d) == set(DIMENSION_NAMES)          # no single magic score
    assert d["adversarial_robustness"]["measurement"] is not None


def test_reliability_card_rejects_unknown_dimension():
    card = ScientificReliabilityCard("x")
    try:
        card.set("magic_trust_score", 0.99, 1)
        raised = False
    except KeyError:
        raised = True
    assert raised


def test_publication_candidate_never_auto_publishes():
    pc = PublicationCandidate(project="p", central_claim="c")
    assert pc.can_publish_automatically is False


def test_full_quality_reaches_human_review_ceiling():
    r = run_reliability("p", reproducibility=0.9, calibration=0.8,
                        evidence_independence=0.8, human_understanding=0.9,
                        provenance=0.9, externally_validated=True)
    assert r["readiness"] == ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value
    assert r["publication_candidate"]["can_publish_automatically"] is False


def test_low_reproducibility_blocks_readiness():
    r = run_reliability("p", reproducibility=0.4)
    assert r["readiness"] == ReadinessLevel.EXPLORATORY.value
    assert r["blockers"]


def test_unresolved_contradiction_blocks_review():
    r = run_reliability("p", reproducibility=0.9, calibration=0.8,
                        evidence_independence=0.8, human_understanding=0.9,
                        provenance=0.9, externally_validated=True,
                        unresolved_contradictions=1)
    assert r["readiness"] != ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value


def test_insufficient_human_understanding_blocks_review():
    r = run_reliability("p", reproducibility=0.9, calibration=0.8,
                        evidence_independence=0.8, human_understanding=0.3,
                        provenance=0.9, externally_validated=True)
    assert r["readiness"] != ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value


# --- Codex-audit regression fixes (Sprint 11) -----------------------------

def test_no_orphan_non_overridable_rules():
    """Every non-overridable rule id must be a real registered gate rule (no typos/orphans)."""
    from acero.epistemic_gate.enforcement import NON_OVERRIDABLE_RULES
    from acero.epistemic_gate.registry import GateRegistry
    ids = set(GateRegistry().rule_ids())
    orphans = sorted(NON_OVERRIDABLE_RULES - ids)
    assert not orphans, f"non-overridable ids not backed by a rule: {orphans}"


def test_mutation_testing_actually_runs_mutations():
    """'all caught' must not be able to masquerade as 'none run'."""
    rep = run_mutation_testing().as_dict()
    assert rep["n"] >= 5 and rep["caught"] == rep["n"]
