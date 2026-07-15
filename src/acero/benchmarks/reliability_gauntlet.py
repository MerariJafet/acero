"""Scientific Reliability Gauntlet (Sprint 11).

Ten end-to-end tracks that check ACERO detects what should be detected, blocks what should
be blocked, and abstains when it should. A result surviving one execution is NOT the same as
surviving an audit — that is what this measures.
"""

from __future__ import annotations

import threading
from typing import Any

from ..epistemic_gate.exceptions import BypassDetected
from ..epistemic_gate.transaction import enforcement_enabled
from ..reliability.calibration import CalibrationObservation, CalibrationRegistry
from ..reliability.evidence import DependencyGraph, Evidence


def track1_clean_pipeline() -> dict[str, Any]:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput
    res = GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(GateInput()))
    return {"outcome": res.outcome.value,
            "passed": res.outcome in (GateOutcome.PASS, GateOutcome.PASS_WITH_WARNINGS)}


def track2_duplicate_evidence() -> dict[str, Any]:
    g = DependencyGraph()
    for i in range(3):
        g.add(Evidence(id=f"r{i}", dataset="SAME_DATA", pipeline="SAME_CODE"))
    n = g.effective_independent_count()
    return {"n_results": 3, "n_independent": n, "counted_as_dependent": n == 1,
            "passed": n == 1}


def track3_faulty_solver() -> dict[str, Any]:
    from ..domains.core.contracts import DomainResult, DomainResultClass
    from ..domains.core.gate_rules import validate_domain_result
    from ..domains.physics.lab import PhysicsLab
    unstable = PhysicsLab().benchmark()["8_unstable_solver_false_evidence"]["detected_instability"]
    v = validate_domain_result(DomainResult("sim", 0, DomainResultClass.SIMULATION),
                               solver_stable_flag=not unstable)
    return {"instability_detected": unstable, "blocked": bool(v), "passed": bool(v)}


def track4_equivalent_models() -> dict[str, Any]:
    from ..reliability.red_team import _inference_blocks
    blocked = _inference_blocks(n_equivalent_models=2, counts_equivalent_as_new=True)
    return {"blocked": blocked, "passed": blocked}


def track5_contaminated_literature() -> dict[str, Any]:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    art = {"all_citations_resolvable": False, "fragments_support_claims": True,
           "uses_retracted_source": True, "preprint_as_consensus": False,
           "commercial_source_as_primary": False, "duplicate_counted_as_independent": False}
    blocked = GlobalGate().check(Stage.LITERATURE, art).outcome == GateOutcome.BLOCKED
    return {"blocked": blocked, "passed": blocked}


def track6_false_causality() -> dict[str, Any]:
    from ..domains.core.contracts import DomainResult, DomainResultClass
    from ..domains.core.gate_rules import validate_domain_result
    v = validate_domain_result(
        DomainResult("assoc", 0.02, DomainResultClass.STATISTICAL_ASSOCIATION),
        claims_causal=True)
    return {"blocked": bool(v), "passed": bool(v)}


def track7_grader_gaming() -> dict[str, Any]:
    from ..understanding.grading.aggregation import GradeVerdict, grade_hybrid
    g = grade_hybrid("Explain why recovering an equation is not a law.",
                     "imposed library fit not a law system identification",
                     ["imposed library", "fit", "not a law", "system identification"],
                     forbidden_elements=["discovered a law of nature"])
    failed = g.verdict != GradeVerdict.PASS and not g.can_reach_mastery
    return {"verdict": g.verdict.value, "failed": failed, "passed": failed}


def track8_miscalibration() -> dict[str, Any]:
    reg = CalibrationRegistry()
    for i in range(12):
        reg.record(CalibrationObservation("m", "probability", predicted_probability=0.9,
                                          actual_outcome=(i % 5 == 0)))
    m = reg.probability_metrics()
    detected = m.get("status") == "ok" and m["ece"] > 0.3
    return {"ece": m.get("ece"), "detected": detected, "passed": detected}


def track9_correct_abstention() -> dict[str, Any]:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput
    from ..inference.models import IdentifiabilityStatus
    gi = GateInput(identifiability=IdentifiabilityStatus.DATA_INSUFFICIENT)
    res = GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(gi))
    abstains = res.outcome == GateOutcome.ESCALATE_TO_HUMAN
    return {"outcome": res.outcome.value, "abstains": abstains, "passed": abstains}


def track10_concurrent_bypass() -> dict[str, Any]:
    """Mutation attempts from threads without a valid gate context must all be blocked."""
    from sqlalchemy import create_engine

    from ..ledger.db import make_session_factory
    from ..ledger.models import Base
    from ..ledger.service import ResearchLedger
    from ..world_model.graph import WorldModel
    from ..world_model.nodes import NodeType

    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    led = ResearchLedger(sf)
    proj = led.create_project("g", domain="physics")
    wm = WorldModel(sf, led, project_id=proj.id)
    n = wm.create(NodeType.HYPOTHESIS, "h")
    blocked = {"count": 0}
    lock = threading.Lock()

    def attempt() -> None:
        with enforcement_enabled():
            try:
                wm.update_belief(n.id, event="sneak", evidence=0.5)
            except BypassDetected:
                with lock:
                    blocked["count"] += 1

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return {"attempts": 8, "blocked": blocked["count"], "passed": blocked["count"] == 8}


def run_gauntlet() -> dict[str, Any]:
    tracks = {
        "1_clean_pipeline": track1_clean_pipeline(),
        "2_duplicate_evidence": track2_duplicate_evidence(),
        "3_faulty_solver": track3_faulty_solver(),
        "4_equivalent_models": track4_equivalent_models(),
        "5_contaminated_literature": track5_contaminated_literature(),
        "6_false_causality": track6_false_causality(),
        "7_grader_gaming": track7_grader_gaming(),
        "8_miscalibration": track8_miscalibration(),
        "9_correct_abstention": track9_correct_abstention(),
        "10_concurrent_bypass": track10_concurrent_bypass(),
    }
    return {"tracks": tracks, "n": len(tracks),
            "passed": sum(1 for t in tracks.values() if t["passed"]),
            "all_passed": all(t["passed"] for t in tracks.values())}
