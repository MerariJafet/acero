"""Capability registry (Sprint 18): the science ACERO claims it can do, with evidence level."""

from __future__ import annotations

from .models import CapabilityStatus, ScientificCapability

# Initial capabilities. Status reflects EVIDENCE, not aspiration; each names its benchmark(s).
_INITIAL: tuple[dict[str, object], ...] = (
    {"name": "literature_retrieval", "domain": "literature", "task_type": "retrieval",
     "benchmark_suite": ["citation_verification"], "status": CapabilityStatus.SUPPORTED,
     "limitations": ["local corpus only; BM25 ranking"]},
    {"name": "citation_verification", "domain": "literature", "task_type": "verification",
     "benchmark_suite": ["citation_verification"], "status": CapabilityStatus.SUPPORTED},
    {"name": "hypothesis_generation", "domain": "discovery", "task_type": "generation",
     "benchmark_suite": ["hidden_dynamics"], "status": CapabilityStatus.SUPPORTED,
     "limitations": ["LLM proposals validated; never treated as evidence"]},
    {"name": "falsifiability_evaluation", "domain": "discovery", "task_type": "scoring",
     "benchmark_suite": ["hidden_dynamics"], "status": CapabilityStatus.SUPPORTED},
    {"name": "experimental_design", "domain": "discovery", "task_type": "design",
     "benchmark_suite": ["hidden_dynamics"], "status": CapabilityStatus.SUPPORTED},
    {"name": "sandbox_execution", "domain": "runtime", "task_type": "execution",
     "benchmark_suite": ["chaos_runtime"], "status": CapabilityStatus.SUPPORTED},
    {"name": "governing_structure_inference", "domain": "inference", "task_type": "inference",
     "benchmark_suite": ["governing_dynamics"], "status": CapabilityStatus.SUPPORTED,
     "limitations": ["polynomial library; coefficients w/o calibrated intervals"]},
    {"name": "analogy_validation", "domain": "cognitive", "task_type": "validation",
     "benchmark_suite": ["cross_domain"], "status": CapabilityStatus.SUPPORTED},
    {"name": "dimensional_analysis", "domain": "cognitive", "task_type": "analysis",
     "benchmark_suite": ["cross_domain"], "status": CapabilityStatus.SUPPORTED},
    {"name": "calibration", "domain": "reliability", "task_type": "calibration",
     "benchmark_suite": ["reliability_gauntlet"], "status": CapabilityStatus.SUPPORTED},
    {"name": "abstention", "domain": "reliability", "task_type": "decision",
     "benchmark_suite": ["reliability_gauntlet"], "status": CapabilityStatus.SUPPORTED},
    {"name": "human_grading", "domain": "understanding", "task_type": "grading",
     "benchmark_suite": ["human_understanding"], "status": CapabilityStatus.SUPPORTED,
     "limitations": ["hybrid deterministic+advisory; Codex never certifies"]},
    {"name": "publication_readiness", "domain": "publication", "task_type": "gating",
     "benchmark_suite": ["publication_review"], "status": CapabilityStatus.SUPPORTED},
    {"name": "astronomy_timeseries_analysis", "domain": "astronomy", "task_type": "analysis",
     "benchmark_suite": ["stellar_variability"], "status": CapabilityStatus.EXPERIMENTAL,
     "limitations": ["single dataset (SILSO); no instrument/pipeline dependence assessed"]},
)


def default_capabilities() -> list[ScientificCapability]:
    return [ScientificCapability(**c) for c in _INITIAL]      # type: ignore[arg-type]


def by_name(name: str) -> ScientificCapability | None:
    for c in default_capabilities():
        if c.name == name:
            return c
    return None
