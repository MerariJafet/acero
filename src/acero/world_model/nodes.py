"""Epistemic node types and the WorldNode (a belief)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id
from .belief import BeliefState


class NodeType(str, Enum):
    CONCEPT = "Concept"
    CLAIM = "Claim"
    EVIDENCE = "Evidence"
    COUNTER_EVIDENCE = "CounterEvidence"
    HYPOTHESIS = "Hypothesis"
    PREDICTION = "Prediction"
    MODEL = "Model"
    EXPERIMENT = "Experiment"
    DATASET = "Dataset"
    VARIABLE = "Variable"
    PARAMETER = "Parameter"
    EQUATION = "Equation"
    LAW = "Law"
    THEORY = "Theory"
    OBSERVATION = "Observation"
    MEASUREMENT = "Measurement"
    METHOD = "Method"
    SIMULATION = "Simulation"
    ASSUMPTION = "Assumption"
    CONSTRAINT = "Constraint"
    QUESTION = "Question"
    CONTRADICTION = "Contradiction"
    NEGATIVE_RESULT = "NegativeResult"
    ANOMALY = "Anomaly"
    OPEN_PROBLEM = "OpenProblem"
    RESEARCH_PROGRAM = "ResearchProgram"
    TOOL = "Tool"
    PUBLICATION = "Publication"
    RESEARCHER = "Researcher"
    DOMAIN = "Domain"
    PHENOMENON = "Phenomenon"


# Node types whose truth-value is a belief we track support for.
BELIEF_TYPES = {
    NodeType.CLAIM, NodeType.HYPOTHESIS, NodeType.MODEL, NodeType.LAW,
    NodeType.THEORY, NodeType.PREDICTION, NodeType.ASSUMPTION, NodeType.PHENOMENON,
    NodeType.EQUATION, NodeType.CONSTRAINT,
}


class WorldNode(BaseModel):
    id: str = Field(default_factory=lambda: new_id("wn"))
    project_id: str
    program_id: str | None = None
    type: NodeType
    label: str
    description: str = ""
    domain: str = "general"
    version: int = 1
    tested: bool = False
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    # type-specific payload (equation string, parameter value, dataset hash, units…)
    data: dict[str, Any] = Field(default_factory=dict)
    provenance: list[str] = Field(default_factory=list)  # provenance event / source ids
    belief: dict[str, Any] = Field(default_factory=lambda: BeliefState().to_dict())

    def belief_state(self) -> BeliefState:
        return BeliefState.from_dict(self.belief)

    def set_belief(self, state: BeliefState) -> None:
        self.belief = state.to_dict()

    @property
    def confidence(self) -> float:
        return float(self.belief.get("confidence", 0.0))

    @property
    def is_belief(self) -> bool:
        return self.type in BELIEF_TYPES


def make_node(project_id: str, ntype: NodeType, label: str, **kw: Any) -> WorldNode:
    return WorldNode(project_id=project_id, type=ntype, label=label, **kw)
