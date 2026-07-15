"""Research Program engine (Sprint 16).

Persists programs via the generic discovery table (kind='research_program', scope '_program'),
manages strategic questions/milestones/budget/retrospectives, and mirrors the program as a
RESEARCH_PROGRAM node in the World Model (guarded write). No external calendar events are
ever created.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from ..provenance.events import ProvenanceAction
from .budget import BudgetGuard
from .models import (
    Milestone,
    ProgramStatus,
    QuestionRole,
    ResearchProgram,
    Retrospective,
    StrategicQuestion,
)
from .portfolio import Portfolio

PROGRAM_SCOPE = "_program"


class ProgramEngine:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    def _save(self, program: ResearchProgram, *, summary: str,
              action: ProvenanceAction = ProvenanceAction.UPDATE) -> None:
        from ..core.clock import now_iso
        program.updated_at = now_iso()
        self._store.put(PROGRAM_SCOPE, "research_program", program.id,
                        program.model_dump(), status=program.status.value,
                        action=action, summary=summary)

    def create(self, mission: str, *, domains: list[str] | None = None,
               central_question: str | None = None) -> ResearchProgram:
        program = ResearchProgram(mission=mission, domains=domains or [])
        if central_question:
            program.central_questions.append(
                StrategicQuestion(text=central_question, role=QuestionRole.CENTRAL))
        self._save(program, summary=f"program created: {mission[:60]}",
                   action=ProvenanceAction.CREATE)
        return program

    def get(self, program_id: str) -> ResearchProgram | None:
        raw = self._store.get(program_id)
        return ResearchProgram(**raw) if raw else None

    def programs(self) -> list[ResearchProgram]:
        return [ResearchProgram(**r)
                for r in self._store.list_objects(PROGRAM_SCOPE, kind="research_program")]

    def add_question(self, program_id: str, text: str, role: QuestionRole,
                     *, depends_on: list[str] | None = None) -> ResearchProgram:
        program = self._require(program_id)
        program.central_questions.append(
            StrategicQuestion(text=text, role=role, depends_on=depends_on or []))
        self._save(program, summary=f"question[{role.value}] added")
        return program

    def add_milestone(self, program_id: str, title: str, *, kind: str = "milestone",
                      target_date: str | None = None) -> ResearchProgram:
        program = self._require(program_id)
        program.milestones.append(Milestone(title=title, kind=kind, target_date=target_date))
        self._save(program, summary=f"milestone added: {title[:40]}")
        return program

    def set_status(self, program_id: str, status: ProgramStatus) -> ResearchProgram:
        program = self._require(program_id)
        program.status = status
        self._save(program, summary=f"status -> {status.value}")
        return program

    def budget_guard(self, program_id: str) -> BudgetGuard:
        program = self._require(program_id)
        return BudgetGuard(program.compute_budget, program.budget_usage)

    def charge_budget(self, program_id: str, resource: str, amount: float) -> ResearchProgram:
        """Charge a resource; BudgetExceeded (no partial charge) if it would overrun."""
        program = self._require(program_id)
        guard = BudgetGuard(program.compute_budget, program.budget_usage)
        guard.charge(resource, amount)               # raises if over the hard limit
        program.budget_usage = guard.usage
        self._save(program, summary=f"charge {resource}+{amount}")
        return program

    def prioritize(self, scored: dict[str, dict[str, float]]) -> Portfolio:
        pf = Portfolio()
        for pid, dims in scored.items():
            pf.add(pid, dims)
        return pf

    def add_retrospective(self, program_id: str, retro: Retrospective) -> ResearchProgram:
        program = self._require(program_id)
        program.retrospectives.append(retro)
        self._save(program, summary=f"retrospective[{retro.cycle}] added")
        return program

    def strategic_view(self, program_id: str) -> dict[str, Any]:
        program = self._require(program_id)
        by_role: dict[str, list[str]] = {}
        for q in program.central_questions:
            by_role.setdefault(q.role.value, []).append(q.text)
        return {"mission": program.mission, "status": program.status.value,
                "questions_by_role": by_role,
                "n_milestones": len(program.milestones),
                "milestones_done": sum(1 for m in program.milestones if m.done),
                "budget": BudgetGuard(program.compute_budget, program.budget_usage).report(),
                "n_retrospectives": len(program.retrospectives),
                "subprojects": program.subprojects}

    def _require(self, program_id: str) -> ResearchProgram:
        program = self.get(program_id)
        if program is None:
            raise KeyError(f"program {program_id} not found")
        return program
