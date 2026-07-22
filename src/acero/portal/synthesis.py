"""Synthesis — turn a hypothesis' executed evidence into accumulated knowledge.

C1: a per-hypothesis SYNTHESIS record — the honest "where does this stand".
C2: the cycle CLOSES into knowledge:
  * every NEW experiment verdict updates the hypothesis' belief node in the
    World Model (versioned, with provenance to the exact experiment; applied
    once per experiment — idempotent across re-syntheses), and
  * an AUTO-DRAFTED DOSSIER per hypothesis (evidence for/against, citations,
    experiments, the critic's standing) appears in the Conclusiones phase.
    Readiness is honest: it is a DRAFT for HUMAN review — approving it stays a
    human act (Sprint 12 publication flow); nothing auto-publishes.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

# belief nudges per verdict (policy-bounded by the World Model itself)
_BELIEF: dict[str, dict[str, Any]] = {
    "supports": {"evidence": 0.5},
    "refutes": {"counter": 0.5, "negative": 1},
    "inconclusive": {"open_question": 1},
}


def _standing(counts: dict[str, int]) -> str:
    supports, refutes = counts.get("supports", 0), counts.get("refutes", 0)
    if refutes and not supports:
        return "DEBILITADA por la evidencia ejecutada"
    if supports and not refutes:
        return "APOYADA por la evidencia ejecutada (candidata, no descubrimiento)"
    if supports and refutes:
        return "EVIDENCIA MIXTA — requiere experimentos discriminantes"
    return "SIN EVIDENCIA EJECUTADA CONCLUYENTE"


def _update_world_model(project_id: str, h: dict[str, Any],
                        exps: list[dict[str, Any]], store: DiscoveryStore,
                        ledger: ResearchLedger, sf: Any) -> dict[str, Any]:
    """Belief node per hypothesis; each completed experiment applied exactly once."""
    from ..world_model.graph import WorldModel
    from ..world_model.nodes import NodeType
    wm = WorldModel(sf, ledger, project_id)

    node_id = h.get("world_node_id") or ""
    if not node_id or wm.get_node(node_id) is None:
        node = wm.create(NodeType.HYPOTHESIS,
                         f"{h.get('tag','')}: {(h.get('title') or '')[:100]}",
                         domain=h.get("kind", "") or "hypothesis")
        node_id = node.id

    applied = set(h.get("synthesized_exp_ids") or [])
    newly = []
    for e in exps:
        verdict = (e.get("result") or {}).get("verdict")
        if e.get("status") != "COMPLETE" or verdict not in _BELIEF or e["id"] in applied:
            continue
        nudge = _BELIEF[verdict]
        wm.update_belief(node_id, event="experiment",
                         evidence=float(nudge.get("evidence", 0.0)),
                         counter=float(nudge.get("counter", 0.0)),
                         negative=int(nudge.get("negative", 0)),
                         open_question=int(nudge.get("open_question", 0)),
                         source=f"experiment:{e['id']}", actor="mission_engine")
        applied.add(e["id"])
        newly.append({"exp_id": e["id"], "verdict": verdict})
    store.update_payload(h["id"], {"world_node_id": node_id,
                                   "synthesized_exp_ids": sorted(applied)})
    final = wm.get_node(node_id)
    return {"node_id": node_id, "applied_now": newly,
            "confidence": final.confidence if final else None}


def _upsert_dossier(project_id: str, h: dict[str, Any], standing: str,
                    counts: dict[str, int], exps: list[dict[str, Any]],
                    latest_crit: dict[str, Any] | None, store: DiscoveryStore,
                    belief: dict[str, Any]) -> str:
    conf = h.get("confrontation") or {}
    ev_for, ev_against = [], []
    for e in exps:
        v = (e.get("result") or {}).get("verdict")
        line = {"experiment": e.get("title", ""), "exp_id": e.get("id", ""),
                "reason": (e.get("result") or {}).get("verdict_reason", "")[:200]}
        if v == "supports":
            ev_for.append(line)
        elif v == "refutes":
            ev_against.append(line)
    if conf.get("argument_for"):
        ev_for.append({"literature": conf["argument_for"][:250]})
    if conf.get("argument_against"):
        ev_against.append({"literature": conf["argument_against"][:250]})

    existing = next((d for d in store.list_objects(project_id, kind="dossier")
                     if d.get("hyp_id") == h["id"]), None)
    crit_block = None
    blocked = False
    if latest_crit:
        objs = latest_crit.get("objections", [])
        sts = latest_crit.get("objections_status") or (["pending"] * len(objs))
        pending = sum(1 for s in sts if s != "resolved")
        crit_block = {"verdict": latest_crit.get("verdict", ""),
                      "objections": objs, "objections_status": sts,
                      "pending": pending,
                      "hard_question": latest_crit.get("hard_question", "")}
        # soft gate: critical unresolved objections block the draft's readiness
        blocked = pending > 0 and latest_crit.get("verdict") in ("debil", "defectuoso")
    readiness = ("BLOQUEADO — objeciones críticas del Revisor sin resolver; "
                 "responde con evidencia antes de revisar"
                 if blocked else "BORRADOR_AUTOMATICO — requiere revisión humana")
    payload = {
        "hyp_id": h["id"], "hyp_tag": h.get("tag", ""),
        "claim": h.get("title", ""),
        "synthesis": f"{h.get('tag','')} v{int(h.get('version',1))}: {standing}",
        "standing": standing, "verdict_counts": counts,
        "evidence_for": ev_for[:8], "evidence_against": ev_against[:8],
        "citations": (conf.get("citations") or [])[:8],
        "critic": crit_block, "blocked_by_critic": blocked,
        "belief_confidence": belief.get("confidence"),
        "world_node_id": belief.get("node_id", ""),
        "readiness": readiness,
        "status": "DRAFT", "updated_at": now_iso(),
    }
    if existing:
        store.update_payload(existing["id"], payload)
        return str(existing["id"])
    did = new_id("dos")
    payload["id"] = did
    store.put(project_id, "dossier", did, payload, status="DRAFT",
              actor="mission_engine",
              summary=f"dossier automático {h.get('tag')}: {standing[:60]}")
    return did


def synthesize_hypothesis(project_id: str, hyp_id: str,
                          session_factory: Any | None = None, *,
                          use_ai: bool = True) -> dict[str, Any]:
    sf = session_factory or default_session_factory()
    ledger = ResearchLedger(sf)
    store = DiscoveryStore(sf, ledger)
    h = store.get(hyp_id)
    if not h:
        return {"ok": False, "error": "hypothesis not found"}

    conf = h.get("confrontation") or {}
    exps = [e for e in store.list_objects(project_id, kind="experiment")
            if e.get("hyp_id") == hyp_id]
    verdicts = [((e.get("result") or {}).get("verdict") or
                 ("plan" if e.get("status") == "PLANNED" else "?")) for e in exps]
    counts = {v: verdicts.count(v) for v in set(verdicts)} if verdicts else {}
    # C3: the critic re-reviews its own objections against the NEW evidence
    try:
        from .critic import CriticAgent
        CriticAgent(sf).resolve_objections(project_id, hyp_id, use_ai=use_ai)
    except Exception:  # noqa: BLE001 - re-review must not kill the mission
        pass
    crits = [c for c in store.list_objects(project_id, kind="critique")
             if c.get("target_id") == hyp_id]
    latest_crit = max(crits, key=lambda c: c.get("created_at") or "", default=None)
    standing = _standing(counts)

    # C2: verdicts → World Model beliefs (idempotent) + auto-dossier draft
    try:
        belief = _update_world_model(project_id, h, exps, store, ledger, sf)
    except Exception as exc:  # noqa: BLE001 - belief update must not kill the mission
        belief = {"node_id": "", "applied_now": [], "confidence": None,
                  "error": str(exc)[:200]}
    dossier_id = _upsert_dossier(project_id, h, standing, counts, exps,
                                 latest_crit, store, belief)

    # C5: measured discrepancies in the executed evidence seed NEW hypotheses
    anomalies_created = 0
    try:
        from .anomalies import AnomalyEngine
        hv = AnomalyEngine(sf).harvest(project_id, use_ai=use_ai)
        anomalies_created = len(hv.get("created", []))
    except Exception:  # noqa: BLE001 - harvesting must not kill the mission
        pass

    summary = (f"{h.get('tag','')} v{int(h.get('version',1))}: {standing}. "
               f"Literatura: {h.get('lit_count', 0)} papers "
               f"(postura {conf.get('stance','sin confrontar')}). "
               f"Experimentos: {len(exps)} ({counts}). "
               f"Creencia WM: {belief.get('confidence')}. "
               f"Revisor: {(latest_crit or {}).get('verdict','sin crítica')}.")

    sid = new_id("syn")
    rec = {"id": sid, "hyp_id": hyp_id, "hyp_tag": h.get("tag", ""),
           "standing": standing, "verdict_counts": counts,
           "n_experiments": len(exps), "lit_count": h.get("lit_count", 0),
           "stance": conf.get("stance", ""),
           "critic_verdict": (latest_crit or {}).get("verdict", ""),
           "belief": belief, "dossier_id": dossier_id,
           "anomaly_hypotheses": anomalies_created,
           "summary": summary, "created_at": now_iso()}
    store.put(project_id, "synthesis", sid, rec, status="ISSUED",
              actor="mission_engine", summary=summary[:150])
    return {"ok": True, "id": sid, "standing": standing, "summary": summary,
            "dossier_id": dossier_id, "belief": belief}
