"""F6: rival theory generator — always ≥2 rivals + differential predictions (offline)."""

from __future__ import annotations

from acero.epistemic.claim_reconstructor import ClaimRecord, EvidenceType
from acero.epistemic.rival_theory_generator import generate_rivals
from acero.epistemic.vulnerability import scan_vulnerabilities
from acero.science.discrimination import design_discriminating_test


def _claim():
    return ClaimRecord(
        claim_id="c1", claim_text="polaridad→permeabilidad",
        exposure_or_input="polaridad", outcome_or_prediction="permeabilidad",
        effect_direction="neg", evidence_type=EvidenceType.OBSERVATIONAL,
        provenance_roots=("R",))


def _confounding_vuln():
    from acero.epistemic.vulnerability import VulnerabilityType
    return next(v for v in scan_vulnerabilities(_claim())
               if v.type is VulnerabilityType.CONFOUNDING)


def test_confounding_generates_covariate_rivals():
    rs = generate_rivals(_confounding_vuln(), _claim(),
                         confounder_candidates=("peso molecular", "lipofilia"))
    assert rs.is_well_posed()               # ≥2 rivals + differential predictions
    assert any("peso molecular" in r for r in rs.rivals)
    assert any("lipofilia" in r for r in rs.rivals)


def test_rivals_feed_a_decisive_test():
    rs = generate_rivals(_confounding_vuln(), _claim(),
                         confounder_candidates=("peso", "logD"))
    test = design_discriminating_test(rs)
    assert test.decisive and test.expected_information_gain() > 0


def test_always_at_least_two_rivals():
    from acero.epistemic.vulnerability import EpistemicVulnerability, VulnerabilityType
    v = EpistemicVulnerability("v", "c1", VulnerabilityType.NOT_REPLICATED, "x",
                               decisive_test="t", cheapest_probe="p")
    rs = generate_rivals(v, _claim())
    assert len(rs.rivals) >= 2 and rs.null and rs.main
