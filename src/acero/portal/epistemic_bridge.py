"""Bridge: run the epistemic Question/EVA pipeline over a project's REAL hypotheses.

Turns each stored hypothesis into a ClaimRecord (evidence type, replication status and
provenance roots derived from its executed experiments), runs the topic→vulnerabilities→
questions→discriminating-test pipeline, and returns a JSON-safe result for the portal.
Read-only and defensive: never mutates the project, never raises to the caller.
"""

from __future__ import annotations

from collections.abc import Callable
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

# An extractor turns ONE hypothesis dict into a dict of ClaimRecord semantic fields
# (exposure_or_input, outcome_or_prediction, mechanism, assumptions, boundary_conditions,
# population_or_domain). A real one calls Codex per hypothesis; the default is the
# deterministic heuristic below. Injectable so the portal can wire Codex and tests stay
# offline. Returns (fields, provenance) where provenance ∈ {"llm","heuristic","fallback"}.
Extractor = Callable[[dict[str, Any]], "tuple[dict[str, Any], str]"]

_CONF_BY_PROVENANCE = {"llm": 1.0, "heuristic": 0.7, "fallback": 0.5}


def _sentences(text: str, n: int = 1) -> str:
    parts = [s.strip() for s in str(text).replace(";", ".").split(".") if s.strip()]
    return ". ".join(parts[:n])


def heuristic_extract(h: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Deterministic per-hypothesis field extraction from its OWN structured content.

    Each hypothesis carries a different argument/doubt/competes_with, so the assumptions
    and mechanism below differ per claim — which makes the downstream vulnerabilities
    claim-specific instead of an identical template. No LLM, no network.
    """
    fields: dict[str, Any] = {}
    argument = str(h.get("argument") or "")
    doubt = str(h.get("doubt") or "")
    tq = str(h.get("trigger_question") or "")
    test_idea = str(h.get("test_idea") or "")
    competes = str(h.get("competes_with") or "")
    if argument:
        fields["mechanism"] = _sentences(argument, 2)[:220]
    assumptions: list[str] = []
    if doubt:
        assumptions.append(f"no se cumple lo que la falsaría: {_sentences(doubt, 1)[:150]}")
    if competes:
        assumptions.append(f"las rivales quedan descartadas: {_sentences(competes, 1)[:120]}")
    if tq:
        assumptions.append(f"la pregunta detonante está bien planteada: {_sentences(tq, 1)[:120]}")
    if assumptions:
        fields["assumptions"] = tuple(assumptions[:3])
    # a test idea that names a range/population gives a real boundary condition
    if test_idea and any(k in test_idea.lower() for k in
                         ("rango", "población", "poblacion", "sub", "bin", "cohorte",
                          "entre", "límite", "limite", "borde")):
        fields["boundary_conditions"] = (_sentences(test_idea, 1)[:140],)
    return fields, "heuristic"


_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "population_or_domain": {"type": "string"},
        "exposure_or_input": {"type": "string"},
        "outcome_or_prediction": {"type": "string"},
        "effect_direction": {"type": "string"},
        "mechanism": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "boundary_conditions": {"type": "array", "items": {"type": "string"}},
    },
    # Codex --output-schema is STRICT: every property must be in `required` (empties
    # are allowed and dropped downstream). Mirrors PLAN_SCHEMA in experiment_factory.
    "required": ["population_or_domain", "exposure_or_input", "outcome_or_prediction",
                 "effect_direction", "mechanism", "assumptions", "boundary_conditions"],
    "additionalProperties": False,
}


def codex_extract(h: dict[str, Any], *, provider: Any | None = None
                  ) -> tuple[dict[str, Any], str]:
    """LLM reconstruction of ONE hypothesis into ClaimRecord fields, per claim.

    Populating exposure/outcome activates the CONFOUNDING vulnerability (which the
    heuristic path cannot infer), giving type-level specificity per claim. Raises on
    failure so the caller degrades to the heuristic (provenance='fallback').
    """
    if provider is None:
        from .experiment_factory import _codex
        provider = _codex()
    title = str(h.get("title") or h.get("description") or "")
    prompt = (
        "Reconstruye ESTA hipótesis científica en campos estructurados (no la critiques, "
        "sólo extrae lo que afirma). Devuelve JSON con: population_or_domain, "
        "exposure_or_input (la variable causal/predictora), outcome_or_prediction (lo "
        "que cambia), effect_direction, mechanism, assumptions (supuestos concretos de los "
        "que depende, específicos de ESTA hipótesis), boundary_conditions (rango/población "
        "donde aplica). Sé específico y fiel al texto; no inventes.\n\n"
        f"Título: {title}\n"
        f"Pregunta detonante: {h.get('trigger_question','')}\n"
        f"Argumento: {h.get('argument','')}\n"
        f"Duda/qué la falsaría: {h.get('doubt','')}\n"
        f"Compite con: {h.get('competes_with','')}\n"
        f"Cómo probarla: {h.get('test_idea','')}")
    out = provider.complete_json(prompt, _EXTRACT_SCHEMA, temperature=0.1)
    fields = {k: v for k, v in out.items() if v}       # drop empties
    return fields, "llm"


def make_codex_extractor() -> Extractor | None:
    """Return a per-hypothesis Codex extractor, or None if Codex is unavailable."""
    try:
        from .experiment_factory import _codex
        _codex()                                        # probe availability
    except Exception:  # noqa: BLE001
        return None
    return lambda h: codex_extract(h)


def _claim_from_hypothesis(h: dict[str, Any], exps: list[dict[str, Any]],
                           *, extractor: Extractor | None = None
                           ) -> tuple[ClaimRecord, str, float]:
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
    # per-hypothesis semantic enrichment (LLM if wired, else deterministic heuristic)
    try:
        fields, provenance = (extractor or heuristic_extract)(h)
    except Exception:  # noqa: BLE001 - a failing LLM extractor degrades, never breaks
        fields, provenance = heuristic_extract(h)
        provenance = "fallback"
    claim = ClaimRecord(
        claim_id=str(h.get("id") or h.get("tag") or "h"),
        claim_text=title, normalized_claim=title[:160],
        population_or_domain=str(fields.get("population_or_domain", "")),
        exposure_or_input=str(fields.get("exposure_or_input", "")),
        outcome_or_prediction=str(fields.get("outcome_or_prediction", "")),
        effect_direction=str(fields.get("effect_direction",
                                        "observada" if supports else "")),
        mechanism=str(fields.get("mechanism", "")),
        assumptions=tuple(fields.get("assumptions", ()) or ()),
        boundary_conditions=tuple(fields.get("boundary_conditions", ()) or ()),
        evidence_type=EvidenceType.OBSERVATIONAL,
        provenance_roots=tuple(sorted(roots)) or (("mixto",) if supports else ()),
        replication_status=rep)
    return claim, provenance, _CONF_BY_PROVENANCE.get(provenance, 0.5)


def eva_for_hypothesis(h: dict[str, Any], exps: list[dict[str, Any]] | None = None,
                       *, extractor: Extractor | None = None) -> list[dict[str, Any]]:
    """EVA vulnerabilities for ONE hypothesis — the shared surface the critic
    (Aristóteles) consumes so it does not re-derive weaknesses from scratch.
    Returns [{type, description, decisive_test, severity}] ranked by priority."""
    claim, _prov, _conf = _claim_from_hypothesis(h, exps or [], extractor=extractor)
    vulns = audit_external(claim).vulnerabilities
    return [{"id": v.vulnerability_id, "type": v.type.value, "description": v.description,
             "decisive_test": v.decisive_test, "severity": round(v.severity, 2)}
            for v in vulns[:6]]


def run_epistemic(project_id: str, session_factory: Any | None = None,
                  *, extractor: Extractor | None = None) -> dict[str, Any]:
    """Run the epistemic pipeline over the project's approved/candidate hypotheses.

    `extractor` (optional) does per-hypothesis semantic reconstruction; when None the
    deterministic `heuristic_extract` is used. The portal can pass a Codex-backed one.
    """
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
        reasoning: dict[str, dict[str, Any]] = {}
        vuln_sets: dict[str, frozenset[str]] = {}
        for h in target_hyps[:8]:
            exps = [e for e in all_exps if e.get("hyp_id") == h.get("id")]
            c, provenance, confidence = _claim_from_hypothesis(h, exps, extractor=extractor)
            claims.append(c)
            rep = audit_external(c)
            eva_by_claim[c.claim_id] = [v.summary() for v in rep.vulnerabilities[:5]]
            # de-dup on CONTENT (type + description), not just type: rival hypotheses
            # legitimately SHARE vulnerability types; a true duplicate shares the wording.
            vuln_sets[c.claim_id] = frozenset(
                f"{v.type.value}:{(v.description or '')[:60]}" for v in rep.vulnerabilities)
            reasoning[c.claim_id] = {
                "provenance": provenance, "confidence": confidence,
                "n_assumptions": len(c.assumptions), "has_mechanism": bool(c.mechanism),
                "vuln_types": sorted(vuln_sets[c.claim_id])}
        # semantic de-dup: flag claims that received an IDENTICAL vulnerability type-set
        dup_groups: list[list[str]] = []
        seen: dict[frozenset[str], list[str]] = {}
        for cid, vs in vuln_sets.items():
            seen.setdefault(vs, []).append(cid)
        for cids in seen.values():
            if len(cids) > 1:
                dup_groups.append(cids)
                for cid in cids:
                    reasoning[cid]["duplicate_with"] = [x for x in cids if x != cid]
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
            "reasoning": reasoning,
            "duplicate_groups": dup_groups,
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
