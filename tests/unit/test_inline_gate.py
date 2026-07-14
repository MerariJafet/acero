"""Sprint 10 tests: the inline epistemic gate (enforcement, transactions, bypass)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from acero.epistemic_gate.enforcement import (
    NON_OVERRIDABLE_RULES,
    GateEnforcer,
    Override,
    OverridePolicy,
)
from acero.epistemic_gate.exceptions import (
    BypassDetected,
    GateBlockedError,
    OverrideNotAllowed,
)
from acero.epistemic_gate.models import Stage
from acero.epistemic_gate.transaction import enforcement_enabled, in_context
from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.ledger.service import ResearchLedger
from acero.world_model.graph import WorldModel
from acero.world_model.nodes import NodeType

_CLEAN = {"updated_by_codex_only": False, "evidence_has_provenance": True,
          "contradiction_ignored": False, "overwrites_history": False,
          "belief_confidence": 0.6, "dependent_counted_as_independent": False,
          "simulation_as_physical_proof": False, "claim_without_limitations": False}


def _wm():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    led = ResearchLedger(sf)
    proj = led.create_project("t", domain="physics")
    return WorldModel(sf, led, project_id=proj.id)


def test_allowed_mutation_runs():
    wm = _wm()
    n = wm.create(NodeType.HYPOTHESIS, "h")
    enf = GateEnforcer()
    gpa, node = enf.enforce(
        action="update_belief", stage=Stage.WORLD_MODEL_UPDATE, artifact=_CLEAN,
        mutation=lambda: wm.update_belief(n.id, event="experiment", evidence=0.3))
    assert gpa.allowed
    assert wm.get_node(n.id).confidence != 0.5      # mutation happened
    assert enf.metrics.allowed == 1


def test_blocked_mutation_leaves_no_state():
    wm = _wm()
    n = wm.create(NodeType.HYPOTHESIS, "h")
    before = wm.get_node(n.id).confidence
    enf = GateEnforcer()
    bad = dict(_CLEAN, evidence_has_provenance=False)
    with pytest.raises(GateBlockedError):
        enf.enforce(action="update_belief", stage=Stage.WORLD_MODEL_UPDATE, artifact=bad,
                    mutation=lambda: wm.update_belief(n.id, event="x", evidence=0.9))
    assert wm.get_node(n.id).confidence == before   # NO partial mutation
    assert enf.metrics.blocked == 1


def test_rejection_is_recorded():
    sink: list = []
    enf = GateEnforcer(rejection_sink=sink.append)
    bad = dict(_CLEAN, evidence_has_provenance=False)
    with pytest.raises(GateBlockedError):
        enf.enforce(action="x", stage=Stage.WORLD_MODEL_UPDATE, artifact=bad,
                    mutation=lambda: None)
    assert len(sink) == 1 and not sink[0].allowed      # attempt is never lost


def test_bypass_detected_on_raw_write():
    wm = _wm()
    n = wm.create(NodeType.HYPOTHESIS, "h")
    with enforcement_enabled():
        with pytest.raises(BypassDetected):
            wm.update_belief(n.id, event="sneak", evidence=0.5)


def test_context_closed_after_enforce():
    wm = _wm()
    n = wm.create(NodeType.HYPOTHESIS, "h")
    GateEnforcer().enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=_CLEAN,
                           mutation=lambda: wm.update_belief(n.id, event="e", evidence=0.1))
    assert not in_context()                            # window closed


def test_override_allowed_on_overridable_blocker():
    enf = GateEnforcer()
    bad = dict(_CLEAN, contradiction_ignored=True)     # overridable blocker
    ov = Override(responsible="Merari", reason="reconciled offline", risk="low",
                  rules_ignored=["contradiction_not_ignored"])
    gpa, _ = enf.enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=bad,
                         mutation=lambda: "done", override=ov)
    assert gpa.allowed and gpa.override is not None
    assert enf.metrics.overrides == 1


def test_override_refused_on_non_overridable():
    enf = GateEnforcer()
    bad = dict(_CLEAN, evidence_has_provenance=False)  # non-overridable (lost provenance)
    ov = Override(responsible="x", reason="y", risk="z", rules_ignored=["evidence_has_provenance"])
    with pytest.raises(OverrideNotAllowed):
        enf.enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=bad,
                    mutation=lambda: None, override=ov)


def test_no_override_policy_blocks_even_with_override():
    enf = GateEnforcer()
    bad = dict(_CLEAN, contradiction_ignored=True)
    ov = Override(responsible="x", reason="y", risk="z", rules_ignored=[])
    with pytest.raises(GateBlockedError):
        enf.enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=bad,
                    mutation=lambda: None, override=ov,
                    override_policy=OverridePolicy.NO_OVERRIDE)


def test_mutation_failure_rolls_back_context():
    enf = GateEnforcer()

    def boom():
        raise RuntimeError("mutation failed")
    with pytest.raises(RuntimeError):
        enf.enforce(action="u", stage=Stage.WORLD_MODEL_UPDATE, artifact=_CLEAN,
                    mutation=boom)
    assert not in_context()                            # context cleaned up on failure


def test_fabrication_rules_are_non_overridable():
    assert "not_reproducible" in NON_OVERRIDABLE_RULES
    assert "missing_provenance" in NON_OVERRIDABLE_RULES
    assert "no_ai_authorship" in NON_OVERRIDABLE_RULES


def test_publication_integrity_rules_are_non_overridable():
    for rid in ("citations_verified", "results_reproducible", "discovery_human_reviewed",
                "central_conclusion_understood"):
        assert rid in NON_OVERRIDABLE_RULES
