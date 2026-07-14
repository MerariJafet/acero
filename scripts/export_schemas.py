#!/usr/bin/env python
"""Export JSON Schemas for the core epistemic entities.

Usage:
  python scripts/export_schemas.py           # write schemas/*.json
  python scripts/export_schemas.py --check    # verify they are up to date (CI gate)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from acero.core.config import repo_root
from acero.epistemology.schemas import (
    Assumption,
    ExecutionRun,
    ExperimentPlan,
    Hypothesis,
    NegativeResult,
    Prediction,
    ResearchProject,
    ResearchQuestion,
    ResearchResult,
    ScientificClaim,
)
from acero.discovery.candidates import HypothesisCandidate
from acero.discovery.experiment_design import ExperimentProposal
from acero.discovery.next_experiment import RecommendedNextExperiment
from acero.discovery.tree import TreeNode
from acero.experiment.prereg import Preregistration
from acero.provenance.events import ProvenanceEvent
from acero.cognitive.analogies.models import ScientificAnalogy
from acero.cognitive.concepts.models import ScientificConcept
from acero.cognitive.first_principles.models import (
    FirstPrinciplesProblem,
    ScientificDerivation,
)
from acero.inference.models import GoverningModelCandidate, StructureInferenceProblem
from acero.world_model.edges import WorldEdge
from acero.world_model.nodes import WorldNode

MODELS = {
    "research_project": ResearchProject,
    "research_question": ResearchQuestion,
    "assumption": Assumption,
    "hypothesis": Hypothesis,
    "prediction": Prediction,
    "experiment_plan": ExperimentPlan,
    "execution_run": ExecutionRun,
    "research_result": ResearchResult,
    "negative_result": NegativeResult,
    "scientific_claim": ScientificClaim,
    "preregistration": Preregistration,
    "provenance_event": ProvenanceEvent,
    # Discovery Engine (Sprints 5–7)
    "hypothesis_candidate": HypothesisCandidate,
    "experiment_proposal": ExperimentProposal,
    "tree_node": TreeNode,
    "recommended_next_experiment": RecommendedNextExperiment,
    # World Model (Sprint 8)
    "world_node": WorldNode,
    "world_edge": WorldEdge,
    # Cognitive Discovery Engine (Sprints 8.5–8.7)
    "scientific_concept": ScientificConcept,
    "scientific_analogy": ScientificAnalogy,
    "first_principles_problem": FirstPrinciplesProblem,
    "scientific_derivation": ScientificDerivation,
    # Governing Structure Inference (Sprints 8.8–8.9)
    "structure_inference_problem": StructureInferenceProblem,
    "governing_model_candidate": GoverningModelCandidate,
}


def render() -> dict[str, str]:
    return {
        name: json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
        for name, model in MODELS.items()
    }


def main() -> int:
    check = "--check" in sys.argv
    out_dir = repo_root() / "schemas"
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = render()
    stale = []
    for name, text in rendered.items():
        path = out_dir / f"{name}.schema.json"
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
    if check:
        if stale:
            print(f"Schemas out of date: {', '.join(stale)}. Run scripts/export_schemas.py.")
            return 1
        print(f"Schemas up to date ({len(rendered)} models). ✓")
        return 0
    print(f"Wrote {len(rendered)} schemas to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
