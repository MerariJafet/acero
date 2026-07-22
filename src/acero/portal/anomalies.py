"""Anomaly engine — new hypotheses born from DATA, not from prompts.

Genuinely new knowledge starts where the data disagrees with expectation. The
factory's executed analyses now report `anomalies` (unexpected residuals,
outliers, subsets behaving differently — with concrete values). This engine
harvests them and turns each one into a CANDIDATE hypothesis whose provenance
points to the exact experiment and the exact discrepancy that motivated it.

Rules: harvested once per experiment (idempotent); the new hypotheses are
PROPOSED candidates like any other — a human still approves them; nothing here
is a finding. Refuted/inconclusive verdicts also count as discrepancy sources
(a refutation with partial passes is exactly where a better question hides).
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

HYP_FROM_ANOMALY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "trigger_question": {"type": "string"},
        "argument": {"type": "string"},
        "doubt": {"type": "string"},
        "test_idea": {"type": "string"},
    },
    "required": ["title", "trigger_question", "argument", "doubt", "test_idea"],
    "additionalProperties": False,
}


class AnomalyEngine:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- detection -------------------------------------------------------------
    def pending_anomalies(self, project_id: str) -> list[dict[str, Any]]:
        """Unharvested discrepancies from COMPLETED experiments."""
        out = []
        for e in self.store.list_objects(project_id, kind="experiment"):
            if e.get("status") != "COMPLETE" or e.get("anomalies_harvested"):
                continue
            res = e.get("result") or {}
            for a in (res.get("anomalies") or []):
                out.append({"exp_id": e["id"], "exp_title": e.get("title", ""),
                            "hyp_tag": e.get("hyp_tag", ""), "anomaly": str(a),
                            "kind": "reported"})
            # a refutation with partial passes is itself a discrepancy worth a question
            if res.get("verdict") in ("refutes", "inconclusive") and \
                    not (res.get("anomalies") or []):
                out.append({"exp_id": e["id"], "exp_title": e.get("title", ""),
                            "hyp_tag": e.get("hyp_tag", ""),
                            "anomaly": f"veredicto {res.get('verdict')}: "
                                       f"{str(res.get('verdict_reason'))[:200]}",
                            "kind": "verdict"})
        return out

    # --- harvest → candidate hypotheses -----------------------------------------
    def harvest(self, project_id: str, *, use_ai: bool = True,
                limit: int = 3) -> dict[str, Any]:
        pend = self.pending_anomalies(project_id)[:limit]
        if not pend:
            return {"ok": True, "created": [],
                    "note": "sin anomalías nuevas en los experimentos ejecutados"}
        base = len(self.store.list_objects(project_id, kind="candidate"))
        created = []
        touched: set[str] = set()
        for i, a in enumerate(pend):
            spec = self._hypothesize(a, use_ai=use_ai)
            hid = new_id("hyp")
            tag = f"H{base + i}"
            payload = {"id": hid, "tag": tag, "title": spec["title"],
                       "description": spec["title"], "kind": "novel",
                       "trigger_question": spec["trigger_question"],
                       "argument": spec["argument"], "doubt": spec["doubt"],
                       "test_idea": spec["test_idea"],
                       "competes_with": a.get("hyp_tag", ""),
                       "origin": "anomaly",
                       "anomaly_provenance": {"exp_id": a["exp_id"],
                                              "exp_title": a["exp_title"],
                                              "anomaly": a["anomaly"]},
                       "provider": spec.get("provider", "deterministic"),
                       "generated": True, "created_at": now_iso(),
                       "status": "PROPOSED", "synthetic": False}
            self.store.put(project_id, "candidate", hid, payload, status="PROPOSED",
                           actor="anomaly_engine",
                           summary=f"🔥 hipótesis desde anomalía de {a['exp_title'][:40]}")
            created.append(payload)
            touched.add(a["exp_id"])
        for eid in touched:
            self.store.update_payload(eid, {"anomalies_harvested": True})
        return {"ok": True, "created": created,
                "disclaimer": "Candidatas nacidas de discrepancias medidas; "
                              "requieren aprobación humana como cualquier hipótesis."}

    def _hypothesize(self, a: dict[str, Any], *, use_ai: bool) -> dict[str, Any]:
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=120)
                if prov.available():
                    out = prov.complete_json(
                        f"En el experimento «{a['exp_title']}» apareció esta "
                        f"DISCREPANCIA MEDIDA: «{a['anomaly']}». Formula UNA hipótesis "
                        "CRÍTICA y comprobable que explique la discrepancia (no la "
                        "descarte). Devuelve title (afirmación falsable), "
                        "trigger_question, argument, doubt (qué la falsaría), "
                        "test_idea (comprobable en la compu). En español. "
                        "Nada es un descubrimiento.",
                        HYP_FROM_ANOMALY_SCHEMA, temperature=0.5)
                    out["provider"] = "codex"
                    return out
            except Exception:  # noqa: BLE001
                pass
        return {"title": f"La discrepancia «{a['anomaly'][:80]}» refleja un efecto "
                         "real no modelado, no un artefacto",
                "trigger_question": "¿Qué produce exactamente esta discrepancia?",
                "argument": "Una desviación medida y reproducible exige explicación.",
                "doubt": "Podría ser sistemático del pipeline o fluctuación esperada.",
                "test_idea": "Re-analizar el subconjunto discrepante con controles "
                             "dedicados y datos independientes",
                "provider": "deterministic"}
