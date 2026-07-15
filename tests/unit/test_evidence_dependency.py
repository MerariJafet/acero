"""Sprint 11 tests: evidence dependency graph, replication levels, quality."""

from __future__ import annotations

from acero.reliability.evidence import (
    INDEPENDENT_REPLICATION_LEVELS,
    DependencyGraph,
    DependencyType,
    Evidence,
    EvidenceQuality,
    ReplicationLevel,
    classify_pair,
    dependency_aware_support,
)


def test_independent_evidence():
    a = Evidence("a", dataset="D1")
    b = Evidence("b", dataset="D2")
    assert classify_pair(a, b).dependency_type == DependencyType.INDEPENDENT


def test_same_dataset_dependent():
    dep = classify_pair(Evidence("a", dataset="D1"), Evidence("b", dataset="D1"))
    assert dep.dependency_type == DependencyType.SAME_DATASET
    assert dep.estimated_strength > 0.5


def test_same_pipeline_dependent():
    dep = classify_pair(Evidence("a", pipeline="P"), Evidence("b", pipeline="P"))
    assert dep.dependency_type == DependencyType.SAME_PIPELINE


def test_same_simulator_dependent():
    dep = classify_pair(Evidence("a", simulator="S"), Evidence("b", simulator="S"))
    assert dep.dependency_type == DependencyType.SAME_SIMULATOR


def test_derived_source_dependent():
    dep = classify_pair(Evidence("a"), Evidence("b", derived_from="a"))
    assert dep.dependency_type == DependencyType.DERIVED_SOURCE


def test_shared_systematic_dependent():
    dep = classify_pair(Evidence("a", systematic="cal_offset"),
                        Evidence("b", systematic="cal_offset"))
    assert dep.dependency_type == DependencyType.SHARED_SYSTEMATIC


def test_clusters_collapse_dependent_evidence():
    g = DependencyGraph()
    for i in range(3):
        g.add(Evidence(id=f"d{i}", dataset="SAME"))
    g.add(Evidence(id="indep", dataset="OTHER"))
    g.build()
    assert g.effective_independent_count() == 2      # 3 dependent + 1 independent


def test_dependency_aware_support_does_not_inflate():
    g = DependencyGraph()
    for i in range(3):
        g.add(Evidence(id=f"d{i}", dataset="SAME"))
    s = dependency_aware_support(g, per_item_support=0.2)
    assert s["naive_support"] > s["dependency_aware_support"]
    assert s["n_independent_groups"] == 1


def test_reexecution_is_not_replication():
    g = DependencyGraph()
    assert not g.counts_as_replication(ReplicationLevel.REEXECUTION)
    assert g.counts_as_replication(ReplicationLevel.DIRECT_REPLICATION)
    assert ReplicationLevel.EXTERNAL_VALIDATION in INDEPENDENT_REPLICATION_LEVELS


def test_quality_never_collapses_silently():
    q = EvidenceQuality(reproducibility=0.9, independence=0.2, calibration=0.5)
    d = q.as_dict()
    assert "reproducibility" in d and "independence" in d
    assert "aggregate_view" in d                       # aggregate is a view, not a verdict
    assert d["independence"] == 0.2                     # components remain visible


def test_shared_analyst_and_method_are_dependencies():
    """Codex-audit fix: correlated human judgement / methodology is not independent."""
    assert classify_pair(Evidence("a", analyst="teamX"),
                         Evidence("b", analyst="teamX")).dependency_type \
        == DependencyType.SHARED_SYSTEMATIC
    assert classify_pair(Evidence("a", method="same_choice"),
                         Evidence("b", method="same_choice")).dependency_type \
        == DependencyType.SHARED_SYSTEMATIC
