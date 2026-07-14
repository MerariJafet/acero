"""Concept Engine tests."""

from __future__ import annotations

import pytest

from acero.cognitive.concepts.engine import CircularDependencyError, ConceptEngine
from acero.cognitive.concepts.models import (
    ApplicabilityRegime,
    ConceptType,
    ConceptualTransformation,
    DefinitionSet,
    ScientificConcept,
)
from acero.world_model.graph import WorldModel


@pytest.fixture()
def ce(session_factory, ledger, project) -> ConceptEngine:
    return ConceptEngine(WorldModel(session_factory, ledger, project.id))


def _temp(project_id):
    return ScientificConcept(
        project_id=project_id, canonical_name="Temperature", aliases=["T"],
        concept_type=ConceptType.PROPERTY,
        definitions=DefinitionSet(lexical="thermal measure",
                                  operational="result of a measurement procedure",
                                  mathematical="<KE> ~ (3/2) k T"),
        assumptions=["local equilibrium"],
        invalid_regimes=[ApplicabilityRegime(label="far from equilibrium",
                                             invalid_conditions=["strongly out of equilibrium"])])


def test_structured_definitions_persist(ce, project):
    ce.create(_temp(project.id))
    got = ce.find("temperature")
    assert got is not None
    assert got.definitions.operational
    assert got.definitions.mathematical
    assert "T" in got.aliases


def test_applicability_regime(ce, project):
    c = ce.create(_temp(project.id))
    assert ce.is_applicable(c.id, ["room temperature"])["applicable"] is True
    assert ce.is_applicable(c.id, ["strongly out of equilibrium"])["applicable"] is False


def test_dependencies_and_query(ce, project):
    t = ce.create(_temp(project.id))
    eq = ce.create(ScientificConcept(project_id=project.id, canonical_name="Thermal equilibrium",
                                     concept_type=ConceptType.STATE))
    ce.add_dependency(t.id, eq.id, "presupposes")
    deps = ce.dependencies(t.id, "presupposes")
    assert deps and deps[0]["target"] == "Thermal equilibrium"
    assert "Temperature" in ce.depends_on_assumption("local equilibrium")


def test_circular_dependency_rejected(ce, project):
    a = ce.create(ScientificConcept(project_id=project.id, canonical_name="A"))
    b = ce.create(ScientificConcept(project_id=project.id, canonical_name="B"))
    ce.add_dependency(a.id, b.id, "requires")
    with pytest.raises(CircularDependencyError):
        ce.add_dependency(b.id, a.id, "requires")


def test_transformation_is_versioned(ce, project):
    t = ce.create(_temp(project.id))
    ce.transform(t.id, ConceptualTransformation(previous_model="heat as fluid",
                                                new_model="heat as energy transfer"))
    got = ce.get(t.id)
    assert len(got.historical_versions) == 1
    assert got.historical_versions[0].assessed_as_progress is None  # not auto-progress


def test_compression_is_explainable(ce, project):
    t = ce.create(_temp(project.id))
    res = ce.compression_score(t.id, phenomena_explained=5, rules_replaced=3,
                               new_predictions=2, exceptions=1)
    assert res["compression_score"] > 0
    assert "heuristic" in res["note"]


def test_compare_shared_structure(ce, project):
    a = ce.create(ScientificConcept(project_id=project.id, canonical_name="Osc",
                                    invariants=["energy"], symmetries=["time_translation"],
                                    dimensions={"T": "-1"}))
    b = ce.create(ScientificConcept(project_id=project.id, canonical_name="RLC",
                                    invariants=["energy"], symmetries=["time_translation"],
                                    dimensions={"T": "-1"}))
    cmp = ce.compare(a.id, b.id)
    assert cmp["shared_invariants"] == ["energy"]
    assert cmp["same_dimensions"]


def test_codex_concept_unverified(ce, project):
    ce.create(ScientificConcept(project_id=project.id, canonical_name="Speculative",
                                generator="codex", sources_verified=False,
                                supporting_sources=["claimed ref"]))
    assert "Speculative" in ce.unverified_concepts()
