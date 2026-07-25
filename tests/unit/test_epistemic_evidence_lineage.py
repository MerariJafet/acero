"""F2: evidence lineage — shared-root evidence collapses to one line (offline)."""

from __future__ import annotations

from acero.epistemic.evidence_lineage import EvidenceItem, EvidenceLineage


def test_five_papers_one_root_are_one_evidence_line():
    lin = EvidenceLineage("c1")
    for i in range(5):
        lin.add(EvidenceItem(f"e{i}", "c1", source=f"paper{i}",
                             dataset_id=f"d{i}", provenance_root="TDC",
                             study_id="caco2_wang"))
    assert lin.n_reported() == 5
    assert lin.n_independent() == 1          # all share the TDC root → one line
    assert lin.summary()["inflation"] == 4


def test_distinct_roots_are_distinct_lines():
    lin = EvidenceLineage("c1")
    lin.add(EvidenceItem("e1", "c1", dataset_id="a", provenance_root="TDC",
                        cohort="A", instrument="Caco-2"))
    lin.add(EvidenceItem("e2", "c1", dataset_id="b", provenance_root="ChEMBL",
                        cohort="B", instrument="PAMPA"))
    assert lin.n_independent() == 2


def test_retracted_evidence_excluded():
    lin = EvidenceLineage("c1")
    lin.add(EvidenceItem("e1", "c1", dataset_id="a", provenance_root="R1", cohort="A"))
    lin.add(EvidenceItem("e2", "c1", dataset_id="b", provenance_root="R2",
                        cohort="B", retracted=True))
    assert lin.n_reported() == 1 and len(lin.retractions()) == 1


def test_contradicting_evidence_tracked():
    lin = EvidenceLineage("c1")
    lin.add(EvidenceItem("e1", "c1", dataset_id="a", provenance_root="R1"))
    lin.add(EvidenceItem("e2", "c1", dataset_id="b", provenance_root="R2",
                        supports=False))
    assert len(lin.contradicting()) == 1


def test_summary_flags_inflation():
    lin = EvidenceLineage("c1")
    for i in range(3):
        lin.add(EvidenceItem(f"e{i}", "c1", dataset_id=f"d{i}", provenance_root="TDC"))
    s = lin.summary()
    assert s["independent_lines"] == 1 and "una" in s["note"]
