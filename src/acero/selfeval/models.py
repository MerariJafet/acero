"""Self-evaluation data models (Sprint 18)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class CapabilityStatus(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    SUPPORTED = "SUPPORTED"
    DEGRADED = "DEGRADED"
    UNRELIABLE = "UNRELIABLE"
    BLOCKED = "BLOCKED"
    DEPRECATED = "DEPRECATED"


class ScientificCapability(BaseModel):
    capability_id: str = Field(default_factory=lambda: new_id("cap"))
    name: str
    domain: str = "general"
    task_type: str = ""
    description: str = ""
    implementation_version: str = "2.0.0-rc1"
    benchmark_suite: list[str] = Field(default_factory=list)
    expected_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_level: str = "benchmark"          # benchmark | anecdotal | none
    last_evaluated: str | None = None
    status: CapabilityStatus = CapabilityStatus.EXPERIMENTAL


class BenchmarkDefinition(BaseModel):
    id: str
    version: str = "v1"
    purpose: str = ""
    fixtures: str = "synthetic/real (see benchmark)"
    truth_source: str = "known-answer or held-out"
    metrics: list[str] = Field(default_factory=list)
    acceptance_thresholds: dict[str, float] = Field(default_factory=dict)
    known_biases: list[str] = Field(default_factory=list)
    leakage_risks: list[str] = Field(default_factory=list)
    compute_budget: str = "local, seconds"
    last_run: str | None = None


class RegressionStatus(str, Enum):
    IMPROVED = "IMPROVED"
    UNCHANGED = "UNCHANGED"
    REGRESSED = "REGRESSED"
    INCONCLUSIVE = "INCONCLUSIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FailureRecord(BaseModel):
    failure_id: str = Field(default_factory=lambda: new_id("fail"))
    source: str
    stage: str = ""
    domain: str = "general"
    category: str = "technical"   # technical|methodological|statistical|epistemological|
                                  # pedagogical|security|ux|runtime|data
    symptom: str = ""
    root_cause: str = ""
    severity: str = "medium"
    reproducible: bool = True
    regression_test: str | None = None
    workaround: str = ""
    status: str = "OPEN"          # OPEN|FIXED|WONTFIX|MONITORING
    related_artifacts: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class ProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED_FOR_EXPERIMENT = "APPROVED_FOR_EXPERIMENT"
    REJECTED = "REJECTED"
    IMPLEMENTED_IN_SANDBOX = "IMPLEMENTED_IN_SANDBOX"
    VALIDATED = "VALIDATED"
    ROLLED_BACK = "ROLLED_BACK"


class ImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: new_id("imp"))
    problem: str
    evidence: list[str] = Field(default_factory=list)
    impacted_capabilities: list[str] = Field(default_factory=list)
    proposed_change: str = ""
    expected_benefit: str = ""
    expected_cost: str = ""
    scientific_risk: str = ""
    technical_risk: str = ""
    tests_required: list[str] = Field(default_factory=list)
    rollback_plan: str = ""
    human_decision: str = "pending"
    status: ProposalStatus = ProposalStatus.PROPOSED
    created_at: str = Field(default_factory=now_iso)
