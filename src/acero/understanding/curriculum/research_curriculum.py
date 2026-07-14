"""Research-derived learning requirements.

Rather than a generic physics/maths course, curricula are derived from REAL ACERO
investigations already implemented (SINDy inference, the oscillator↔RLC analogy, the
sunspot analysis). Each requirement is tied to concrete equations, code, and assumptions
in the investigation, with a criticality and a required mastery level.
"""

from __future__ import annotations

from ..models import Criticality, KnowledgeStatus, ResearchLearningRequirement
from .concept_graph import ConceptGraph

# (concept, reason, criticality, equations, code, required_level, blocking)
_Spec = tuple[str, str, Criticality, list[str], list[str], KnowledgeStatus, bool]

# Prerequisite edges shared across the research curricula (src depends on dst).
_EDGES: tuple[tuple[str, str, str], ...] = (
    ("regression", "linear_algebra", "mathematically_depends_on"),
    ("regularization", "regression", "conceptually_depends_on"),
    ("sparse_identification", "regression", "conceptually_depends_on"),
    ("sparse_identification", "regularization", "conceptually_depends_on"),
    ("sparse_identification", "derivative_estimation", "requires"),
    ("sparse_identification", "collinearity", "requires"),
    ("identifiability", "collinearity", "conceptually_depends_on"),
    ("governing_structure", "sparse_identification", "conceptually_depends_on"),
    ("governing_structure", "identifiability", "requires"),
    ("governing_structure", "imposed_library", "requires"),
    ("collinearity", "linear_algebra", "mathematically_depends_on"),
    ("derivative_estimation", "noise", "requires"),
    ("extrapolation", "governing_structure", "conceptually_depends_on"),
    ("analogy_structure", "dimensional_analysis", "requires"),
    ("analogy_structure", "conserved_quantity", "requires"),
    ("regime_of_validity", "analogy_structure", "conceptually_depends_on"),
    ("periodicity", "fourier_analysis", "requires"),
    ("quasiperiodicity", "periodicity", "conceptually_depends_on"),
    ("mechanism_vs_pattern", "periodicity", "conceptually_depends_on"),
)


def base_concept_graph() -> ConceptGraph:
    g = ConceptGraph()
    for s, d, r in _EDGES:
        g.add(s, d, r)
    return g


def _req(project: str, concept: str, reason: str, crit: Criticality,
         prereqs: list[str], eqs: list[str], code: list[str], asmpt: list[str],
         level: KnowledgeStatus, blocking: bool) -> ResearchLearningRequirement:
    return ResearchLearningRequirement(
        research_project_id=project, concept=concept, reason_required=reason,
        criticality=crit, prerequisite_concepts=prereqs, related_equations=eqs,
        related_code=code, related_assumptions=asmpt,
        required_mastery_level=level, blocking=blocking)


def sindi_requirements(project_id: str) -> list[ResearchLearningRequirement]:
    """What a human must understand to responsibly accept a SINDy inference."""
    g = base_concept_graph()
    C = Criticality
    K = KnowledgeStatus
    concepts: list[tuple[str, str, Criticality, list[str], list[str], KnowledgeStatus, bool]] = [
        ("derivative_estimation",
         "coefficients depend on estimated derivatives, which amplify noise",
         C.HIGH, ["dx/dt ≈ (x_{i+1}-x_{i-1})/2h"],
         ["inference/data/derivatives.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("regularization",
         "ridge suppresses blow-up from collinear library terms",
         C.HIGH, ["min ||Θξ - ẋ||² + λ||ξ||²"],
         ["inference/discovery/sparse_identification.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("collinearity",
         "conserved quantities make library columns dependent → unstable coefficients",
         C.HIGH, ["x² + v²/4 = const"],
         ["inference/discovery/invariants.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("identifiability",
         "some parameters cannot be pinned down from the given data",
         C.BLOCKING, ["cond(Θᵀ Θ)"],
         ["inference/model_selection/identifiability.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("imposed_library",
         "recovered terms come from a library WE imposed; it is not a discovered law",
         C.BLOCKING, [],
         ["inference/libraries/terms.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("noise",
         "noise degrades derivative and coefficient estimates gracefully, not abruptly",
         C.MEDIUM, [],
         ["inference/data/observations.py"], K.PROCEDURALLY_COMPETENT, False),
        ("extrapolation",
         "a model that fits in-range may fail outside it; extrapolation needs a test",
         C.HIGH, [],
         ["inference/audit/gate.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("governing_structure",
         "recovering terms ≠ finding the mechanism; declare the inference level",
         C.BLOCKING, ["ẋ = f(x)"],
         ["inference/engine.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
    ]
    out: list[ResearchLearningRequirement] = []
    for name, reason, crit, eqs, code, level, blocking in concepts:
        out.append(_req(project_id, name, reason, crit,
                        g.prerequisites_of(name), eqs, code,
                        ["library is polynomial", "derivatives from same data"],
                        level, blocking))
    return out


def analogy_requirements(project_id: str) -> list[ResearchLearningRequirement]:
    """Oscillator↔RLC: what to understand before transferring a prediction."""
    g = base_concept_graph()
    C, K = Criticality, KnowledgeStatus
    specs: list[_Spec] = [
        ("analogy_structure", "the mapping is structural (same ODE), not physical identity",
         C.HIGH, ["m ẍ + c ẋ + k x = 0", "L q̈ + R q̇ + q/C = 0"],
         ["cognitive/analogies/structure.py"], K.CONCEPTUALLY_UNDERSTOOD, True),
        ("conserved_quantity", "know what is conserved (energy) and its electrical analogue",
         C.MEDIUM, ["½k x² + ½m v²"], ["inference/discovery/invariants.py"],
         K.PROCEDURALLY_COMPETENT, False),
        ("regime_of_validity", "state where the analogy breaks (nonlinearity, saturation)",
         C.BLOCKING, [], ["cognitive/analogies/validation.py"],
         K.CONCEPTUALLY_UNDERSTOOD, True),
    ]
    return [_req(project_id, n, reason, crit, g.prerequisites_of(n), eqs, code,
                 ["linear, lumped-element regime"], level, blocking)
            for n, reason, crit, eqs, code, level, blocking in specs]


def sunspot_requirements(project_id: str) -> list[ResearchLearningRequirement]:
    """SILSO sunspots: periodicity is not mechanism."""
    g = base_concept_graph()
    C, K = Criticality, KnowledgeStatus
    specs: list[_Spec] = [
        ("periodicity", "an ~11.2yr period is a pattern in the data",
         C.MEDIUM, [], ["benchmarks/real_astronomy_inference.py"],
         K.PROCEDURALLY_COMPETENT, False),
        ("quasiperiodicity", "cycle length/amplitude vary → not a clean sinusoid",
         C.MEDIUM, [], ["benchmarks/real_astronomy_inference.py"],
         K.CONCEPTUALLY_UNDERSTOOD, False),
        ("mechanism_vs_pattern", "11.2yr does NOT demonstrate the solar dynamo",
         C.BLOCKING, [], ["benchmarks/real_astronomy_inference.py"],
         K.CONCEPTUALLY_UNDERSTOOD, True),
    ]
    return [_req(project_id, n, reason, crit, g.prerequisites_of(n), eqs, code,
                 ["observational series", "missing months"], level, blocking)
            for n, reason, crit, eqs, code, level, blocking in specs]


CURRICULA = {
    "sindy": sindi_requirements,
    "analogy": analogy_requirements,
    "sunspots": sunspot_requirements,
}


def requirements_for(kind: str, project_id: str) -> list[ResearchLearningRequirement]:
    if kind not in CURRICULA:
        raise KeyError(f"unknown research curriculum {kind!r}; have {sorted(CURRICULA)}")
    return CURRICULA[kind](project_id)
