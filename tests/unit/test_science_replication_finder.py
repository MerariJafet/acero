"""Replication-source finder — independent-root candidates, certified (offline)."""

from __future__ import annotations

import json

from acero.science import replication_finder as rf
from acero.science.independence_graph import DatasetProvenance, IndependenceKind


def _tdc_caco2():
    return DatasetProvenance("caco2_wang", assay_source="caco2_wang",
                             repository="TDC", provenance_root="TDC/HarvardDataverse")


def test_root_for_generalist_repo_is_per_record():
    assert rf.root_for("Zenodo", "12345") == "Zenodo:12345"
    assert rf.root_for("TDC") == "TDC/HarvardDataverse"


def test_finds_independent_root_candidates_for_permeability():
    cands = rf.find_replication_sources("permeabilidad Caco-2", _tdc_caco2())
    assert cands, "debe proponer fuentes de replicación"
    # a ChEMBL candidate has a DIFFERENT root than TDC → replication-capable
    chembl = next(c for c in cands if c.repository == "ChEMBL")
    assert chembl.provenance_root == "ChEMBL/EBI"
    assert chembl.replication_capable
    assert chembl.independence_kind >= IndependenceKind.DIFF_COHORT


def test_same_root_candidate_is_not_replication_capable():
    # a candidate that shares the TDC root must be rejected as non-independent
    target = _tdc_caco2()
    g = rf.IndependenceGraph()
    g.add(target)
    g.add(DatasetProvenance("other_tdc", provenance_root="TDC/HarvardDataverse",
                            repository="TDC"))
    assert not g.is_replication("caco2_wang", "other_tdc")


def test_live_search_merges_zenodo_hits_with_fake_opener(monkeypatch):
    class Resp:
        def read(self):
            return json.dumps({"hits": {"hits": [
                {"id": 999, "metadata": {"title": "Caco-2 permeability replication set"}}]}
            }).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    import acero.portal.data_resolver as dr
    monkeypatch.setattr(dr.urllib.request, "urlopen", lambda req, timeout=0: Resp())
    cands = rf.find_replication_sources("caco2 permeability", _tdc_caco2(),
                                        live_search=True)
    zc = [c for c in cands if c.reference == "zenodo:999"]
    assert zc and zc[0].provenance_root == "Zenodo:999" and zc[0].replication_capable


def test_candidates_sorted_replication_and_fetchable_first():
    cands = rf.find_replication_sources("permeabilidad Caco-2", _tdc_caco2())
    # the first candidate is replication-capable
    assert cands[0].replication_capable
    assert all("repository" in c.summary() for c in cands)
