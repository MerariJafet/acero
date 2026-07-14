"""Sprint 9 tests: prerequisite graph and research-aware curriculum."""

from __future__ import annotations

import pytest

from acero.understanding.curriculum.concept_graph import ConceptGraph
from acero.understanding.curriculum.research_curriculum import (
    base_concept_graph,
    requirements_for,
)


def test_prerequisites_are_transitive():
    g = base_concept_graph()
    prereqs = g.prerequisites_of("governing_structure")
    assert "sparse_identification" in prereqs
    assert "regression" in prereqs           # transitive through sparse_identification


def test_missing_prerequisites():
    g = base_concept_graph()
    missing = g.missing_prerequisites("sparse_identification", known={"regression"})
    assert "regularization" in missing
    assert "regression" not in missing


def test_cycle_detection():
    g = ConceptGraph()
    g.add("a", "b", "requires")
    g.add("b", "c", "requires")
    g.add("c", "a", "requires")
    cyc = g.find_cycle()
    assert cyc is not None and set(cyc) == {"a", "b", "c"}


def test_no_cycle_in_base_graph():
    assert base_concept_graph().find_cycle() is None


def test_minimum_path_is_topological():
    g = base_concept_graph()
    order = g.minimum_path("sparse_identification", known={"linear_algebra"})
    assert order[-1] == "sparse_identification"
    # regression appears before sparse_identification
    assert order.index("regression") < order.index("sparse_identification")


def test_minimum_path_rejects_cycle():
    g = ConceptGraph()
    g.add("a", "b")
    g.add("b", "a")
    with pytest.raises(ValueError):
        g.minimum_path("a", known=set())


def test_foundational_concepts_are_leaves():
    g = base_concept_graph()
    found = g.foundational_concepts()
    assert "linear_algebra" in found
    assert "sparse_identification" not in found


def test_unnecessary_dependency_detected():
    g = ConceptGraph()
    g.add("a", "b", "requires")
    g.add("b", "c", "requires")
    g.add("a", "c", "requires")           # redundant: a->b->c already implies a->c
    redundant = g.unnecessary_dependencies()
    assert any(e.src == "a" and e.dst == "c" for e in redundant)


def test_requirements_are_anchored_to_research():
    reqs = requirements_for("sindy", "proj1")
    assert reqs
    # every requirement ties to a real equation, code file, or assumption
    for r in reqs:
        assert r.related_equations or r.related_code or r.related_assumptions


def test_requirements_include_blocking_concept():
    reqs = requirements_for("sindy", "proj1")
    assert any(r.blocking for r in reqs)
    assert any(r.concept == "imposed_library" for r in reqs)


def test_unknown_curriculum_raises():
    with pytest.raises(KeyError):
        requirements_for("nope", "p")
