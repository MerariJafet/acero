"""Gate Bypass Benchmark (Sprint 10).

Attempts seven ways to slip a defective mutation past the inline gate. ALL must be
blocked: a direct World-Model write, evidence without a source, closing a non-reproducible
run, promoting a surface analogy, resolving a misconception without new evidence, exporting
a genetic causal claim, and accepting a chemistry prediction that violates mass balance.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine

from ..domains.core.contracts import DomainResult, DomainResultClass
from ..domains.core.gate_rules import validate_domain_result
from ..epistemic_gate.enforcement import GateEnforcer
from ..epistemic_gate.exceptions import BypassDetected, GateBlockedError
from ..epistemic_gate.integration.world_model import GatedWorldModel
from ..epistemic_gate.transaction import enforcement_enabled
from ..ledger.db import make_session_factory
from ..ledger.models import Base
from ..ledger.service import ResearchLedger
from ..world_model.graph import WorldModel
from ..world_model.nodes import NodeType


def _fresh_wm() -> WorldModel:
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    led = ResearchLedger(sf)
    proj = led.create_project("bypass", domain="physics")
    return WorldModel(sf, led, project_id=proj.id)


def attempt_direct_world_write() -> bool:
    """1. Mutate the World Model directly, skipping the gate → BypassDetected."""
    wm = _fresh_wm()
    n = wm.create(NodeType.HYPOTHESIS, "x")
    try:
        with enforcement_enabled():
            wm.update_belief(n.id, event="sneak", evidence=0.9)
        return False
    except BypassDetected:
        return True


def attempt_evidence_without_source() -> bool:
    """2. Accept a belief update whose evidence has no provenance → BLOCKED."""
    wm = _fresh_wm()
    n = wm.create(NodeType.HYPOTHESIS, "x")
    g = GatedWorldModel(wm, GateEnforcer())
    art = {"updated_by_codex_only": False, "evidence_has_provenance": False,
           "contradiction_ignored": False, "overwrites_history": False,
           "belief_confidence": 0.6, "dependent_counted_as_independent": False,
           "simulation_as_physical_proof": False, "claim_without_limitations": False}
    try:
        g.update_belief_gated(n.id, artifact=art, event="experiment", evidence=0.3)
        return False
    except GateBlockedError:
        return True


def _inference_blocked(artifact_overrides: dict[str, Any]) -> bool:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput

    art = artifact_from_gate_input(GateInput(**artifact_overrides))
    res = GlobalGate().check(Stage.INFERENCE, art)
    return res.outcome == GateOutcome.BLOCKED


def attempt_close_nonreproducible() -> bool:
    """3. Close a non-reproducible run → BLOCKED."""
    return _inference_blocked({"reproduced": False})


def attempt_promote_surface_analogy() -> bool:
    """4. Promote a surface-only analogy for transfer → domain analogy rule blocks."""
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage

    art = {"surface_only_used_for_transfer": True, "units_compatible": True,
           "broken_structure_declared": True, "transferred_prediction_tested": True,
           "has_regime_of_validity": True, "misleading_as_explanation": False}
    return GlobalGate().check(Stage.ANALOGY, art).outcome == GateOutcome.BLOCKED


def attempt_resolve_misconception_without_evidence() -> bool:
    """5. Resolve a misconception with no new evidence → refused by the resolver."""
    from ..understanding.assessment.grading import build_evidence
    from ..understanding.learner.misconceptions import detect, resolves
    from ..understanding.models import EvidenceType

    m = detect("recovering the equation is discovering a law", learner_id="l")[0]
    weak, _ = build_evidence("l", m.concept, EvidenceType.EXPLAIN_OWN_WORDS, "t",
                             "unrelated text", ["imposed", "library", "fit"])
    return not resolves(m, weak)         # True = correctly NOT resolved


def attempt_export_genetic_causal() -> bool:
    """6. Export a genetic association as a causal claim → domain rule blocks."""
    result = DomainResult("association", 0.03, DomainResultClass.STATISTICAL_ASSOCIATION)
    return bool(validate_domain_result(result, claims_causal=True))


def attempt_accept_mass_violation() -> bool:
    """7. Accept a chemistry prediction that violates mass balance → domain rule blocks."""
    result = DomainResult("reaction", "unbalanced", DomainResultClass.SIMULATION)
    return bool(validate_domain_result(result, mass_balanced=False))


def run_gate_bypass() -> dict[str, Any]:
    checks = {
        "1_direct_world_write": attempt_direct_world_write(),
        "2_evidence_without_source": attempt_evidence_without_source(),
        "3_close_nonreproducible": attempt_close_nonreproducible(),
        "4_promote_surface_analogy": attempt_promote_surface_analogy(),
        "5_resolve_misconception_no_evidence": attempt_resolve_misconception_without_evidence(),
        "6_export_genetic_causal": attempt_export_genetic_causal(),
        "7_accept_mass_violation": attempt_accept_mass_violation(),
    }
    return {"checks": checks, "all_blocked": all(checks.values()),
            "n_blocked": sum(checks.values()), "n": len(checks)}
