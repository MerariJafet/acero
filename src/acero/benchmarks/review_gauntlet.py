"""Human Scientific Review Gauntlet (Sprint 12).

End-to-end cases for the review → gated-export workflow. Export must be BLOCKED unless every
precondition holds, and must never publish automatically. One case reaches an approved local
export for external human review — the ceiling.
"""

from __future__ import annotations

from typing import Any

from ..publication.dossier import DossierEvidence
from ..publication.engine import build_dossier
from ..publication.export import ExportBlocked, evaluate_export, export_dossier
from ..publication.review import HumanReviewSession, ReviewDecision, ReviewError


def _reviewed(dossier, reviewer="Merari", approve=True, ack=True, comprehension=True):
    r = HumanReviewSession(dossier_id=dossier.id, reviewer=reviewer,
                           comprehension_ok=comprehension)
    if ack:
        for s in ("central_claim", "main_evidence", "main_counter_evidence",
                  "limitations", "reliability", "what_remains_to_validate_externally"):
            r.acknowledge(s)
    decision = (ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW if approve
                else ReviewDecision.REQUEST_CHANGES)
    try:
        r.record(decision, dossier=dossier,
                 reasons=["reviewed; evidence and limitations understood"])
    except ReviewError:
        pass
    return r


def _ready_dossier(**kw):
    return build_dossier("proj", "damped oscillation recovered as ẋ=v, v̇=−4x−0.5v",
                         externally_validated=True,
                         supporting=[DossierEvidence("e1", "clean recovery", "supporting")],
                         counter=[DossierEvidence("c1", "noise degrades fit", "counter")],
                         limitations=["computational only", "polynomial library"], **kw)


def case_not_reviewed() -> dict[str, Any]:
    d = _ready_dossier()
    dec = evaluate_export(d, None)
    return {"blocked": not dec.allowed, "passed": not dec.allowed}


def case_not_ready() -> dict[str, Any]:
    d = build_dossier("proj", "claim", reproducibility=0.4,
                      limitations=["computational only"])
    dec = evaluate_export(d, _reviewed(d))
    return {"readiness": d.readiness, "blocked": not dec.allowed, "passed": not dec.allowed}


def case_no_comprehension() -> dict[str, Any]:
    d = _ready_dossier(human_understanding=0.3)
    dec = evaluate_export(d, _reviewed(d, comprehension=False))
    return {"blocked": not dec.allowed, "passed": not dec.allowed}


def case_ai_reviewer() -> dict[str, Any]:
    d = _ready_dossier()
    # an AI reviewer cannot record an approval
    ai = HumanReviewSession(dossier_id=d.id, reviewer="ACERO", comprehension_ok=True)
    for s in ("central_claim", "main_evidence", "main_counter_evidence",
              "limitations", "reliability", "what_remains_to_validate_externally"):
        ai.acknowledge(s)
    try:
        ai.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])
        refused = False
    except ReviewError:
        refused = True
    # and even a tampered reviewer field is blocked at export time
    r = HumanReviewSession(dossier_id=d.id, reviewer="Merari", comprehension_ok=True)
    r.reviewer = "acero"
    dec = evaluate_export(d, r)
    return {"review_refused": refused, "export_blocked": not dec.allowed,
            "passed": refused and not dec.allowed}


def case_unresolved_contradiction() -> dict[str, Any]:
    d = _ready_dossier(unresolved_contradictions=1)
    dec = evaluate_export(d, _reviewed(d))
    return {"blocked": not dec.allowed, "passed": not dec.allowed}


def case_approved_export(tmp_dir: str) -> dict[str, Any]:
    d = _ready_dossier()
    r = _reviewed(d)
    try:
        res = export_dossier(d, r, tmp_dir)
        return {"exported": True, "auto_published": res["auto_published"],
                "passed": res["auto_published"] is False}
    except ExportBlocked as exc:
        return {"exported": False, "blockers": exc.blockers, "passed": False}


def run_review_gauntlet(tmp_dir: str) -> dict[str, Any]:
    cases = {
        "1_not_reviewed": case_not_reviewed(),
        "2_not_ready": case_not_ready(),
        "3_no_comprehension": case_no_comprehension(),
        "4_ai_reviewer": case_ai_reviewer(),
        "5_unresolved_contradiction": case_unresolved_contradiction(),
        "6_approved_local_export": case_approved_export(tmp_dir),
    }
    return {"cases": cases, "n": len(cases),
            "passed": sum(1 for c in cases.values() if c["passed"]),
            "all_passed": all(c["passed"] for c in cases.values())}
