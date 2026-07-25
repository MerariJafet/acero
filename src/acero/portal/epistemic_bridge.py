"""Bridge: run the epistemic Question/EVA pipeline over a project's REAL hypotheses.

Turns each stored hypothesis into a ClaimRecord (evidence type, replication status and
provenance roots derived from its executed experiments), runs the topic→vulnerabilities→
questions→discriminating-test pipeline, and returns a JSON-safe result for the portal.
Read-only and defensive: never mutates the project, never raises to the caller.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from ..epistemic.claim_reconstructor import (
    ClaimRecord,
    EvidenceType,
    ReplicationStatus,
)
from ..epistemic.eva import audit_external
from ..epistemic.pipeline import run_pipeline
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger


def _claim_from_hypothesis(h: dict[str, Any], exps: list[dict[str, Any]]) -> ClaimRecord:
    supports = [e for e in exps if (e.get("result") or {}).get("verdict") == "supports"]
    roots = {str(e.get("data_source") or "").split(":")[0] for e in supports
             if e.get("data_source")}
    if any((e.get("result") or {}).get("verdict") for e in exps):
        rep = (ReplicationStatus.INDEPENDENT if len(roots) >= 2
               else ReplicationStatus.INTERNAL_ONLY if supports
               else ReplicationStatus.NONE)
    else:
        rep = ReplicationStatus.NONE
    title = str(h.get("title") or h.get("description") or "")
    return ClaimRecord(
        claim_id=str(h.get("id") or h.get("tag") or "h"),
        claim_text=title, normalized_claim=title[:160],
        exposure_or_input="", outcome_or_prediction="",
        effect_direction="observada" if supports else "",
        evidence_type=EvidenceType.OBSERVATIONAL,
        provenance_roots=tuple(sorted(roots)) or (("mixto",) if supports else ()),
        replication_status=rep)


def run_epistemic(project_id: str, session_factory: Any | None = None) -> dict[str, Any]:
    """Run the epistemic pipeline over the project's approved/candidate hypotheses."""
    try:
        sf = session_factory or default_session_factory()
        ledger = ResearchLedger(sf)
        store = DiscoveryStore(sf, ledger)
        project = ledger.get_project(project_id)
        hyps = [h for h in store.list_objects(project_id, kind="candidate")]
        # prefer approved hypotheses; else all
        approved = [h for h in hyps if (h.get("status") or "") == "APPROVED"]
        target_hyps = approved or hyps
        all_exps = [e for e in store.list_objects(project_id, kind="experiment")]
        claims = []
        eva_by_claim: dict[str, list[dict[str, Any]]] = {}
        for h in target_hyps[:8]:
            exps = [e for e in all_exps if e.get("hyp_id") == h.get("id")]
            c = _claim_from_hypothesis(h, exps)
            claims.append(c)
            rep = audit_external(c)
            eva_by_claim[c.claim_id] = [v.summary() for v in rep.vulnerabilities[:5]]
        if not claims:
            return {"ok": False, "error": "sin hipótesis para analizar; genera hipótesis primero"}
        topic = (project.title if project else "investigación")
        res = run_pipeline(topic, claims,
                           confounder_candidates=("una covariable no medida",
                                                  "un sesgo de selección"))
        questions = [{
            "text": e.ranked.question.question_text,
            "family": e.ranked.question.family.value,
            "priority": round(e.priority, 3),
            "target_vulnerability": e.ranked.question.target_vulnerability,
            "why_it_matters": e.ranked.question.why_it_matters,
            "components": e.ranked.card.components(),
        } for e in res.portfolio]
        test = res.discriminating_test
        return {
            "ok": True, "topic": topic, "n_claims": len(claims),
            "n_vulnerabilities": res.n_vulnerabilities,
            "state": res.state.name, "ready": res.ready_for_exploratory,
            "questions": questions,
            "eva": eva_by_claim,
            "discriminating_test": ({
                "bits": round(test.expected_information_gain(), 2),
                "decisive": test.decisive,
                "separates": len(set(test.outcome_favors.values())),
            } if test else None),
            "honesty": ("Preguntas generadas desde las vulnerabilidades de tus hipótesis. "
                        "No son evidencia; priorizan por valor informativo, no por sonar "
                        "llamativas. El techo sigue siendo la revisión humana."),
        }
    except Exception as exc:  # noqa: BLE001 - never break the portal
        return {"ok": False, "error": str(exc)[:200]}
