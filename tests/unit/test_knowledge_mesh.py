"""Scientific Knowledge Mesh — schema + registry (offline) and live connector (gated)."""

from __future__ import annotations

import pytest

from acero.knowledge_mesh import ObjectType, ScientificObject
from acero.knowledge_mesh import sources as src

# --- offline (always run) --------------------------------------------------

def test_epistemic_separation_flags_acero_generated():
    obs = ScientificObject(object_type=ObjectType.OBSERVATION, title="x")
    inf = ScientificObject(object_type=ObjectType.ACERO_INFERENCE, title="y")
    assert obs.is_acero_generated is False
    assert inf.is_acero_generated is True


def test_object_type_enum_covers_required_types():
    names = {t.value for t in ObjectType}
    assert {"OBSERVATION", "PEER_REVIEWED_ARTICLE", "PREPRINT", "DATASET", "RETRACTED_WORK",
            "ACERO_INFERENCE", "ACERO_HYPOTHESIS", "HYPOTHESIS", "NEGATIVE_RESULT"} <= names


def test_seed_registry_has_no_invented_placeholder():
    reg = src.registry()
    assert len(reg) >= 8
    for s in reg:
        assert s.canonical_domain and "." in s.canonical_domain     # real domains
        assert s.documentation_url.startswith("http")
        assert s.api_base_url.startswith("http")


def test_provenance_is_recorded():
    o = ScientificObject(object_type=ObjectType.DATASET, title="d")
    o.add_provenance("connector:test", "fetch", "x")
    assert o.provenance and o.provenance[0].agent == "connector:test"


# --- live (network-gated) --------------------------------------------------

def _online(url: str) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "acero-test"}), timeout=10)
        return True
    except Exception:  # noqa: BLE001
        return False


def test_health_check_verifies_a_real_source():
    if not _online("https://api.crossref.org/works/10.1038/nphys1170"):
        pytest.skip("offline")
    s = src.get_source("crossref")
    r = src.health_check(s)
    assert r["ok"] is True and r["http_status"] == 200


def test_crossref_lookup_real_doi():
    from acero.knowledge_mesh.connectors import crossref
    if not _online("https://api.crossref.org/works/10.1038/nphys1170"):
        pytest.skip("offline")
    obj = crossref.lookup_doi("10.1038/nphys1170", check_retraction=False)
    assert obj is not None
    assert obj.identifiers["doi"] == ["10.1038/nphys1170"]
    assert obj.object_type in (ObjectType.PEER_REVIEWED_ARTICLE, ObjectType.UNKNOWN)


def test_crossref_detects_known_retraction():
    from acero.knowledge_mesh.connectors import crossref
    doi = "10.1016/S0140-6736(97)11096-0"    # Wakefield 1998, retracted
    if not _online("https://api.crossref.org/works/" + doi.replace("/", "%2F")):
        pytest.skip("offline")
    obj = crossref.lookup_doi(doi)
    assert obj is not None
    assert obj.integrity_status == "retracted"
    assert obj.object_type == ObjectType.RETRACTED_WORK


def test_crossref_unknown_doi_is_not_invented():
    from acero.knowledge_mesh.connectors import crossref
    if not _online("https://api.crossref.org/works/10.1038/nphys1170"):
        pytest.skip("offline")
    assert crossref.lookup_doi("10.9999/this-doi-does-not-exist-acero") is None
