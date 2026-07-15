"""Research Program data models (Sprint 16)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class ProgramStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class QuestionRole(str, Enum):
    CENTRAL = "central"
    INSTRUMENTAL = "instrumental"
    PREREQUISITE = "prerequisite"
    ENABLING = "enabling"
    DISCARDED = "discarded"
    PAUSED = "paused"


class StrategicQuestion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("q"))
    text: str
    role: QuestionRole = QuestionRole.INSTRUMENTAL
    depends_on: list[str] = Field(default_factory=list)
    rationale: str = ""


class Milestone(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ms"))
    title: str
    kind: str = "milestone"            # milestone|review|experiment_window|literature_refresh
                                        # |calibration_review|red_team_cycle|human_learning
    target_date: str | None = None     # ISO; humans set real dates — ACERO never creates
                                        # external calendar events
    done: bool = False
    notes: str = ""


class ComputeBudget(BaseModel):
    cpu_core_hours: float = 0.0
    gpu_hours: float = 0.0
    ram_gb: float = 0.0
    storage_gb: float = 0.0
    llm_tokens: int = 0
    download_mb: float = 0.0
    human_hours: float = 0.0


class BudgetUsage(BaseModel):
    cpu_core_hours: float = 0.0
    gpu_hours: float = 0.0
    ram_gb: float = 0.0
    storage_gb: float = 0.0
    llm_tokens: int = 0
    download_mb: float = 0.0
    human_hours: float = 0.0


class Retrospective(BaseModel):
    id: str = Field(default_factory=lambda: new_id("retro"))
    cycle: str
    learned: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    dead_hypotheses: list[str] = Field(default_factory=list)
    missing_tools: list[str] = Field(default_factory=list)
    beliefs_changed: list[str] = Field(default_factory=list)
    not_worth_cost: list[str] = Field(default_factory=list)
    next_to_investigate: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class ResearchProgram(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prog"))
    mission: str
    domains: list[str] = Field(default_factory=list)
    central_questions: list[StrategicQuestion] = Field(default_factory=list)
    theories: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    subprojects: list[str] = Field(default_factory=list)      # project ids
    milestones: list[Milestone] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    compute_budget: ComputeBudget = Field(default_factory=ComputeBudget)
    budget_usage: BudgetUsage = Field(default_factory=BudgetUsage)
    learning_plan: list[str] = Field(default_factory=list)
    collaboration_plan: list[str] = Field(default_factory=list)
    publication_plan: list[str] = Field(default_factory=list)
    status: ProgramStatus = ProgramStatus.DRAFT
    retrospectives: list[Retrospective] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
