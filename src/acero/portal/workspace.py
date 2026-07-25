"""Research Workspace service (Sprint 23).

Drives the full research flow — program → project → question → hypotheses →
approval → experiment → gate → results → World Model → learning → dossier — by
calling the SAME protected services the CLI uses. No method here writes to
persistence directly; every write goes through ``ResearchLedger``,
``ProgramEngine``, ``DiscoveryStore`` or ``WorldModel`` (all gate-guarded).

The hypothesis generation and the toy experiment are deterministic so the
Playwright E2E flow is reproducible; they are clearly labelled synthetic.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger
from ..program.engine import ProgramEngine
from ..program.models import QuestionRole
from ..provenance.events import ProvenanceAction


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


class WorkspaceService:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)
        self.programs = ProgramEngine(self.store)

    # --- program / project ------------------------------------------------
    def create_program(self, mission: str, domains: list[str] | None = None) -> dict[str, Any]:
        p = self.programs.create(mission, domains=domains or ["general"])
        return {"id": p.id, "mission": p.mission, "status": p.status.value}

    def create_project(self, title: str, *, domain: str = "general",
                       program_id: str | None = None, topic: str = "") -> dict[str, Any]:
        proj = self.ledger.create_project(title, domain=domain)
        if topic.strip():
            # the research topic/question — the free-text prompt that seeds hypotheses
            self.store.put(proj.id, "brief", new_id("brief"),
                           {"topic": topic.strip()}, status="ISSUED", actor="human",
                           summary=f"tema de investigación: {topic.strip()[:80]}")
        if program_id:
            self.store.put(proj.id, "program_link", new_id("link"),
                           {"program_id": program_id, "project_id": proj.id},
                           status="LINKED", actor="human",
                           summary=f"link project {proj.id} to program {program_id}")
        return {"id": proj.id, "title": proj.title, "domain": proj.domain,
                "topic": topic.strip()}

    def add_question(self, program_id: str, text: str) -> dict[str, Any]:
        p = self.programs.add_question(program_id, text, QuestionRole.CENTRAL)
        q = p.central_questions[-1]
        return {"program_id": program_id, "question_id": q.id, "text": q.text}

    # --- hypotheses (deterministic synthetic) -----------------------------
    def generate_hypotheses(self, project_id: str, question: str) -> list[dict[str, Any]]:
        rng = _seed(question)
        templates = [
            ("H0", "null: observed structure is noise + trend"),
            ("H1", "a periodic component explains the signal"),
            ("H2", "a known mechanism reproduces the observation"),
            ("H3", "an artifact of preprocessing explains it"),
        ]
        out = []
        for i, (tag, desc) in enumerate(templates):
            hid = new_id("hyp")
            payload = {"id": hid, "tag": tag, "description": desc,
                       "question": question, "prior": round(0.1 + ((rng >> i) % 7) / 10.0, 3),
                       "synthetic": True, "status": "PROPOSED"}
            self.store.put(project_id, "candidate", hid, payload, status="PROPOSED",
                           actor="system", summary=f"hypothesis {tag}")
            out.append(payload)
        return out

    def approve_hypothesis(self, hyp_id: str, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("approving a hypothesis requires a stated reason")
        self.store.set_status(hyp_id, "APPROVED", actor="human",
                              summary=f"approved: {reason}",
                              action=ProvenanceAction.UPDATE)
        obj = self.store.get(hyp_id) or {}
        return {"id": hyp_id, "status": "APPROVED", "reason": reason, "tag": obj.get("tag")}

    # --- experiment + gate ------------------------------------------------
    def run_experiment(self, project_id: str, hyp_id: str) -> dict[str, Any]:
        """A small deterministic synthetic experiment; result stored as an artifact."""
        rng = _seed(hyp_id)
        r2 = round(0.5 + (rng % 50) / 100.0, 3)
        eid = new_id("exp")
        artifact = {"id": eid, "hypothesis_id": hyp_id, "r2": r2,
                    "n_points": 400, "synthetic": True,
                    "dimensions_valid": True, "train_test_disjoint": True,
                    "reproduced": True, "codex_treated_as_evidence": False}
        self.store.put(project_id, "experiment", eid, artifact, status="RUN",
                       actor="system", summary=f"experiment for {hyp_id}")
        return artifact

    def gate_check(self, artifact: dict[str, Any]) -> dict[str, Any]:
        """Run the REAL global gate on an inference artifact (observable block)."""
        from ..epistemic_gate.engine import GlobalGate
        from ..epistemic_gate.models import Stage
        from ..epistemic_gate.rules.inference import artifact_from_gate_input
        from ..inference.audit.gate import GateInput

        gi = GateInput(
            dimensions_valid=bool(artifact.get("dimensions_valid", True)),
            train_test_disjoint=bool(artifact.get("train_test_disjoint", True)),
            reproduced=bool(artifact.get("reproduced", True)),
            codex_treated_as_evidence=bool(artifact.get("codex_treated_as_evidence", False)),
        )
        return GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(gi)).as_dict()

    # --- world model + learning + dossier ---------------------------------
    def update_world_model(self, project_id: str, label: str) -> dict[str, Any]:
        from ..world_model.graph import WorldModel
        from ..world_model.nodes import NodeType

        wm = WorldModel(self._sf, self.ledger, project_id)
        node = wm.create(NodeType.CLAIM, label, confidence=0.5)
        return {"node_id": node.id, "label": node.label, "confidence": node.confidence}

    def dossier(self, project_id: str, claim: str) -> dict[str, Any]:
        from ..publication.dossier import DossierEvidence
        from ..publication.engine import build_dossier

        d = build_dossier(
            project_id, claim, externally_validated=False, reproducibility=0.6,
            supporting=[DossierEvidence("e1", "synthetic recovery", "supporting")],
            counter=[DossierEvidence("c1", "single synthetic run", "counter")],
            limitations=["synthetic; not experimental validation; not a discovery"])
        dd = d.as_dict()
        out = {"id": dd.get("id"), "claim": claim,
               "readiness": dd.get("readiness") or dd.get("readiness_level"),
               "can_publish_automatically": False}
        # persist so the project's Estado tab can show it (requires human review)
        self.store.put(project_id, "dossier", str(dd.get("id") or new_id("dossier")),
                       {**out, "status": "AWAITING_HUMAN_REVIEW"},
                       status="AWAITING_HUMAN_REVIEW", actor="system",
                       summary=f"dossier generado: {claim[:60]}")
        return out
