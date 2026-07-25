"""EP1+EP2: claim reconstruction + EVA vulnerability scanner (offline, deterministic)."""

from __future__ import annotations

from acero.epistemic.claim_reconstructor import (
    ClaimRecord,
    EvidenceType,
    ReconstructionRequest,
    ReplicationStatus,
    reconstruct_claim,
)
from acero.epistemic.vulnerability import (
    VulnerabilityType,
    scan_vulnerabilities,
    surface,
)


def _obs_claim(**over) -> ClaimRecord:
    base = dict(
        claim_id="c1", claim_text="la polaridad predice menor permeabilidad",
        exposure_or_input="polaridad", outcome_or_prediction="permeabilidad",
        effect_direction="negativa", evidence_type=EvidenceType.OBSERVATIONAL,
        supporting_sources=("tdc",), provenance_roots=("TDC",),
        replication_status=ReplicationStatus.INTERNAL_ONLY)
    base.update(over)
    return ClaimRecord(**base)


def test_reconstruct_understands_before_criticizing():
    req = ReconstructionRequest(topic="permeabilidad", known_fields={
        "exposure_or_input": "polaridad", "outcome_or_prediction": "permeabilidad",
        "evidence_type": "observational", "provenance_roots": ("TDC",)})
    rec = reconstruct_claim(req, "c1")
    assert rec.evidence_type is EvidenceType.OBSERVATIONAL
    assert rec.n_independent_sources() == 1
    assert "n_independent_sources" in rec.summary()


def test_eva_flags_single_source_and_no_replication():
    vs = scan_vulnerabilities(_obs_claim())
    types = {v.type for v in vs}
    assert VulnerabilityType.SINGLE_SOURCE in types
    assert VulnerabilityType.NOT_REPLICATED in types


def test_observational_claim_flags_confounding_and_reverse():
    vs = scan_vulnerabilities(_obs_claim())
    types = {v.type for v in vs}
    assert VulnerabilityType.CONFOUNDING in types
    assert VulnerabilityType.REVERSE_CAUSATION in types


def test_every_vulnerability_is_actionable():
    vs = scan_vulnerabilities(_obs_claim())
    assert vs and all(v.actionable for v in vs)      # each carries a probe/test
    assert all(v.decisive_test or v.cheapest_probe for v in vs)


def test_boundaries_and_mechanism_suppress_those_vulnerabilities():
    clean = _obs_claim(boundary_conditions=("rango 200-500 Da",),
                       mechanism="difusión pasiva por membrana")
    types = {v.type for v in scan_vulnerabilities(clean)}
    assert VulnerabilityType.UNJUSTIFIED_EXTRAPOLATION not in types
    assert VulnerabilityType.AMBIGUOUS_MECHANISM not in types


def test_priority_orders_by_severity_times_testability():
    vs = scan_vulnerabilities(_obs_claim())
    prios = [v.priority for v in vs]
    assert prios == sorted(prios, reverse=True)      # sorted desc
    s = surface(_obs_claim())
    assert s["n_actionable"] >= 1 and s["top"]
