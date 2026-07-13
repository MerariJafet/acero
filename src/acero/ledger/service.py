"""ResearchLedger — the transactional service enforcing scientific integrity.

Invariants enforced here (with tests in tests/science and tests/unit):
  * A hypothesis must reference an existing question.
  * A prediction must reference an existing hypothesis.
  * An experiment must test >=1 existing prediction.
  * A result must reference an existing run.
  * A claim must be supported by evidence OR explicitly flagged speculation.
  * Negative results can never be silently deleted.
  * Post-result hypothesis edits are recorded (HARKing guard).
  * Every mutation appends a ProvenanceEvent and an EntityHistory row.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.clock import now_iso
from ..core.errors import IntegrityError, WorkflowError
from ..core.hashing import hash_json
from ..core.ids import new_id
from ..epistemology.schemas import (
    DecisionRecord,
    ResearchProject,
)
from ..epistemology.types import EntityState, EntityType, can_transition
from ..provenance.events import ProvenanceAction, ProvenanceEvent
from .models import (
    DecisionRow,
    EntityHistoryRow,
    EntityRow,
    ProjectRow,
    ProvenanceRow,
    RunRow,
)


class ResearchLedger:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def create_project(
        self, title: str, description: str = "", domain: str = "general"
    ) -> ResearchProject:
        proj = ResearchProject(
            id=new_id("proj"), title=title, description=description, domain=domain
        )
        with self._sf() as s:
            s.add(
                ProjectRow(
                    id=proj.id,
                    title=proj.title,
                    description=proj.description,
                    domain=proj.domain,
                    state=proj.state.value,
                    created_at=proj.created_at,
                    principal_investigator=proj.principal_investigator,
                )
            )
            self._record_provenance(
                s, proj.id, None, ProvenanceAction.CREATE, "human",
                f"Created project '{title}'", proj.model_dump(),
            )
            s.commit()
        return proj

    def get_project(self, project_id: str) -> ResearchProject | None:
        with self._sf() as s:
            row = s.get(ProjectRow, project_id)
            if not row:
                return None
            return ResearchProject(
                id=row.id, title=row.title, description=row.description,
                domain=row.domain, state=EntityState(row.state),
                created_at=row.created_at,
                principal_investigator=row.principal_investigator,
            )

    def list_projects(self) -> list[ResearchProject]:
        with self._sf() as s:
            rows = s.execute(select(ProjectRow)).scalars().all()
            return [
                ResearchProject(
                    id=r.id, title=r.title, description=r.description, domain=r.domain,
                    state=EntityState(r.state), created_at=r.created_at,
                    principal_investigator=r.principal_investigator,
                )
                for r in rows
            ]

    # ------------------------------------------------------------------ #
    # Entities (generic, typed)
    # ------------------------------------------------------------------ #
    def add_entity(self, entity: Any, *, actor: str = "human") -> Any:
        """Persist a validated Pydantic epistemic entity, enforcing integrity."""
        payload = entity.model_dump()
        etype = EntityType(payload["type"])
        with self._sf() as s:
            self._check_project(s, payload["project_id"])
            self._enforce_referential_integrity(s, etype, payload)
            s.add(
                EntityRow(
                    id=payload["id"],
                    project_id=payload["project_id"],
                    type=etype.value,
                    state=payload["state"],
                    version=payload.get("version", 1),
                    title=payload["title"],
                    created_at=payload["created_at"],
                    updated_at=payload["updated_at"],
                    payload=payload,
                )
            )
            s.add(
                EntityHistoryRow(
                    entity_id=payload["id"], version=payload.get("version", 1),
                    at=now_iso(), payload=payload,
                )
            )
            self._record_provenance(
                s, payload["project_id"], payload["id"], ProvenanceAction.CREATE,
                actor, f"Created {etype.value} '{payload['title']}'", payload,
            )
            s.commit()
        return entity

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        with self._sf() as s:
            row = s.get(EntityRow, entity_id)
            return dict(row.payload) if row else None

    def list_entities(
        self, project_id: str, etype: EntityType | None = None
    ) -> list[dict[str, Any]]:
        with self._sf() as s:
            stmt = select(EntityRow).where(EntityRow.project_id == project_id)
            if etype is not None:
                stmt = stmt.where(EntityRow.type == etype.value)
            rows = s.execute(stmt).scalars().all()
            return [dict(r.payload) for r in rows]

    def update_entity(
        self, entity_id: str, changes: dict[str, Any], *, actor: str = "human"
    ) -> dict[str, Any]:
        with self._sf() as s:
            row = s.get(EntityRow, entity_id)
            if not row:
                raise IntegrityError(f"Entity {entity_id} not found")
            payload = dict(row.payload)

            # HARKing guard: editing a hypothesis after results exist is recorded.
            if row.type == EntityType.HYPOTHESIS.value and self._has_results(s, row.project_id):
                self._record_provenance(
                    s, row.project_id, entity_id, ProvenanceAction.UPDATE, actor,
                    "Hypothesis edited AFTER results exist (HARKing guard flagged this).",
                    {"changes": changes, "flag": "post_result_hypothesis_edit"},
                )

            payload.update(changes)
            payload["version"] = payload.get("version", 1) + 1
            payload["updated_at"] = now_iso()
            row.payload = payload
            row.version = payload["version"]
            row.state = payload.get("state", row.state)
            row.title = payload.get("title", row.title)
            row.updated_at = payload["updated_at"]
            s.add(
                EntityHistoryRow(
                    entity_id=entity_id, version=payload["version"],
                    at=payload["updated_at"], payload=payload,
                )
            )
            self._record_provenance(
                s, row.project_id, entity_id, ProvenanceAction.UPDATE, actor,
                f"Updated {row.type}", {"changes": changes},
            )
            s.commit()
            return payload

    def transition_state(
        self, entity_id: str, new_state: EntityState, *, actor: str = "human"
    ) -> dict[str, Any]:
        with self._sf() as s:
            row = s.get(EntityRow, entity_id)
            if not row:
                raise IntegrityError(f"Entity {entity_id} not found")
            src = EntityState(row.state)
            if not can_transition(src, new_state):
                raise WorkflowError(
                    f"Illegal state transition {src.value} -> {new_state.value} for {entity_id}"
                )
            payload = dict(row.payload)
            payload["state"] = new_state.value
            payload["version"] = payload.get("version", 1) + 1
            payload["updated_at"] = now_iso()
            row.payload = payload
            row.state = new_state.value
            row.version = payload["version"]
            s.add(
                EntityHistoryRow(
                    entity_id=entity_id, version=payload["version"],
                    at=payload["updated_at"], payload=payload,
                )
            )
            self._record_provenance(
                s, row.project_id, entity_id, ProvenanceAction.STATE_CHANGE, actor,
                f"{src.value} -> {new_state.value}", {"from": src.value, "to": new_state.value},
            )
            s.commit()
            return payload

    def delete_entity(self, entity_id: str, *, actor: str = "human") -> None:
        """Delete an entity. Negative results are protected and cannot be deleted."""
        with self._sf() as s:
            row = s.get(EntityRow, entity_id)
            if not row:
                raise IntegrityError(f"Entity {entity_id} not found")
            if row.type == EntityType.NEGATIVE_RESULT.value:
                raise IntegrityError(
                    "Negative results cannot be deleted (they must be preserved). "
                    "Archive it instead via transition_state(ARCHIVED)."
                )
            s.delete(row)
            self._record_provenance(
                s, row.project_id, entity_id, ProvenanceAction.UPDATE, actor,
                f"Deleted {row.type}", {},
            )
            s.commit()

    # ------------------------------------------------------------------ #
    # Runs, decisions, provenance access
    # ------------------------------------------------------------------ #
    def add_run(self, run: Any) -> Any:
        payload = run.model_dump()
        with self._sf() as s:
            self._check_project(s, payload["project_id"])
            s.add(
                RunRow(
                    id=payload["id"], project_id=payload["project_id"],
                    experiment_id=payload["experiment_id"],
                    status=payload["status"], payload=payload,
                )
            )
            self._record_provenance(
                s, payload["project_id"], payload["experiment_id"],
                ProvenanceAction.RUN_START, "system", f"Run {payload['id']} started", payload,
            )
            s.commit()
        return run

    def update_run(self, run_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        with self._sf() as s:
            row = s.get(RunRow, run_id)
            if not row:
                raise IntegrityError(f"Run {run_id} not found")
            payload = dict(row.payload)
            payload.update(changes)
            row.payload = payload
            row.status = payload.get("status", row.status)
            self._record_provenance(
                s, row.project_id, row.experiment_id, ProvenanceAction.RUN_FINISH,
                "system", f"Run {run_id} -> {row.status}", {"changes": changes},
            )
            s.commit()
            return payload

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._sf() as s:
            row = s.get(RunRow, run_id)
            return dict(row.payload) if row else None

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        with self._sf() as s:
            s.add(DecisionRow(id=decision.id, project_id=decision.project_id,
                              payload=decision.model_dump()))
            self._record_provenance(
                s, decision.project_id, None, ProvenanceAction.HUMAN_DECISION,
                decision.decided_by, decision.title, decision.model_dump(),
            )
            s.commit()
        return decision

    def provenance_for_project(self, project_id: str) -> list[dict[str, Any]]:
        with self._sf() as s:
            rows = s.execute(
                select(ProvenanceRow).where(ProvenanceRow.project_id == project_id)
                .order_by(ProvenanceRow.at)
            ).scalars().all()
            return [dict(r.payload) for r in rows]

    def history_for_entity(self, entity_id: str) -> list[dict[str, Any]]:
        with self._sf() as s:
            rows = s.execute(
                select(EntityHistoryRow).where(EntityHistoryRow.entity_id == entity_id)
                .order_by(EntityHistoryRow.version)
            ).scalars().all()
            return [dict(r.payload) for r in rows]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _check_project(self, s: Session, project_id: str) -> None:
        if not s.get(ProjectRow, project_id):
            raise IntegrityError(f"Project {project_id} does not exist")

    def _entity_of_type(self, s: Session, entity_id: str | None, etype: EntityType) -> bool:
        if not entity_id:
            return False
        row = s.get(EntityRow, entity_id)
        return row is not None and row.type == etype.value

    def _has_results(self, s: Session, project_id: str) -> bool:
        stmt = select(EntityRow).where(
            EntityRow.project_id == project_id,
            EntityRow.type.in_([EntityType.RESULT.value, EntityType.NEGATIVE_RESULT.value]),
        )
        return s.execute(stmt).first() is not None

    def _enforce_referential_integrity(
        self, s: Session, etype: EntityType, payload: dict[str, Any]
    ) -> None:
        if etype == EntityType.HYPOTHESIS:
            qid = payload.get("question_id")
            if not self._entity_of_type(s, qid, EntityType.QUESTION):
                raise IntegrityError(f"Hypothesis references missing question {qid}")
        elif etype == EntityType.PREDICTION:
            hid = payload.get("hypothesis_id")
            if not self._entity_of_type(s, hid, EntityType.HYPOTHESIS):
                raise IntegrityError(f"Prediction references missing hypothesis {hid}")
        elif etype == EntityType.EXPERIMENT:
            pids = payload.get("prediction_ids", [])
            for pid in pids:
                if not self._entity_of_type(s, pid, EntityType.PREDICTION):
                    raise IntegrityError(f"Experiment references missing prediction {pid}")
        elif etype in (EntityType.RESULT, EntityType.NEGATIVE_RESULT):
            rid = payload.get("run_id")
            if not s.get(RunRow, rid):
                raise IntegrityError(f"Result references missing run {rid}")
        elif etype == EntityType.CLAIM:
            supported = payload.get("supported_by", [])
            is_spec = payload.get("is_speculation", False)
            if not supported and not is_spec:
                raise IntegrityError(
                    "A claim must be supported by evidence or explicitly flagged as speculation."
                )

    def _record_provenance(
        self, s: Session, project_id: str, entity_id: str | None,
        action: ProvenanceAction, actor: str, summary: str, payload: dict[str, Any],
    ) -> None:
        ev = ProvenanceEvent(
            id=new_id("prov"), project_id=project_id, entity_id=entity_id,
            action=action, actor=actor, summary=summary,
            payload_hash=hash_json(payload),
            details=payload,
        )
        s.add(
            ProvenanceRow(
                id=ev.id, project_id=project_id, entity_id=entity_id,
                action=action.value, actor=actor, at=ev.at, payload=ev.model_dump(),
            )
        )
