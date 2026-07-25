"""L1: independence graph — computed from provenance, split never = replication."""

from __future__ import annotations

from acero.science.independence_graph import (
    DatasetProvenance,
    IndependenceGraph,
    IndependenceKind,
)


def test_holdout_split_is_never_replication():
    g = IndependenceGraph()
    g.add(DatasetProvenance("caco2_full", study_id="caco2_wang",
                            provenance_root="TDC"))
    g.add(DatasetProvenance("caco2_holdout", is_partition_of="caco2_full",
                            study_id="caco2_wang", provenance_root="TDC"))
    v = g.independence("caco2_full", "caco2_holdout")
    assert v.kind is IndependenceKind.SAME_PARTITION
    assert not v.is_replication_capable
    assert not g.is_replication("caco2_full", "caco2_holdout")


def test_same_source_different_study_not_independent():
    g = IndependenceGraph()
    g.add(DatasetProvenance("d1", study_id="s1", assay_source="ChEMBL",
                            repository="ebi"))
    g.add(DatasetProvenance("d2", study_id="s2", assay_source="ChEMBL",
                            repository="ebi"))
    v = g.independence("d1", "d2")
    assert v.kind is IndependenceKind.SAME_SOURCE and not v.is_replication_capable
    assert "assay/fuente" in v.shares


def test_different_cohort_and_source_is_independent():
    g = IndependenceGraph()
    g.add(DatasetProvenance("caco2", assay_source="caco2_wang", cohort="A",
                            instrument="Caco-2", laboratory="lab1"))
    g.add(DatasetProvenance("pampa", assay_source="pampa_ncats", cohort="B",
                            instrument="PAMPA", laboratory="lab2"))
    v = g.independence("caco2", "pampa")
    assert v.kind >= IndependenceKind.DIFF_COHORT
    assert v.is_replication_capable and g.is_replication("caco2", "pampa")


def test_shared_provenance_root_blocks_independence():
    g = IndependenceGraph()
    g.add(DatasetProvenance("a", study_id="sa", provenance_root="ROOT",
                            cohort="A"))
    g.add(DatasetProvenance("b", study_id="sb", provenance_root="ROOT",
                            cohort="B"))
    v = g.independence("a", "b")
    assert v.kind is IndependenceKind.SAME_STUDY   # same root → not independent
    assert "raíz de procedencia" in v.shares


def test_unknown_provenance_is_conservative():
    g = IndependenceGraph()
    v = g.independence("x", "y")               # neither registered
    assert not v.is_replication_capable        # default to NOT independent


def test_explain_lists_shared_and_differing_dimensions():
    g = IndependenceGraph()
    g.add(DatasetProvenance("a", assay_source="ChEMBL", laboratory="l1", cohort="A"))
    g.add(DatasetProvenance("b", assay_source="ChEMBL", laboratory="l2", cohort="B"))
    txt = g.independence("a", "b").explain()
    assert "comparten" in txt and "difieren" in txt
