"""CCC-5: independence levels + claim compiler / overclaim linter (offline)."""

from __future__ import annotations

from acero.science.claim_compiler import (
    DESIGN_CAUSAL,
    DESIGN_PREDICTIVE_EXTERNAL,
    ClaimLevel,
    EvidenceProfile,
    compile_claim,
    max_claim,
    scan_overclaims,
)
from acero.science.independence import (
    EvidenceStrength,
    IndependenceLedger,
    IndependenceLevel,
)
from acero.science.preregistration import Regime


def test_level1_check_gives_only_weak_strength():
    led = IndependenceLedger()
    led.add(IndependenceLevel.SAME_ALGO_OTHER_IMPL, "otra impl", agreed=True)
    assert led.strength() is EvidenceStrength.WEAK


def test_strong_needs_method_diff_and_independent_dataset():
    led = IndependenceLedger()
    led.add(IndependenceLevel.OTHER_STAT_METHOD, "bayes vs freq", agreed=True)
    assert led.strength() is EvidenceStrength.MODERATE      # method only
    led.add(IndependenceLevel.OTHER_DATASET_COHORT, "cohorte B", agreed=True)
    assert led.strength() is EvidenceStrength.STRONG        # + independent data
    assert led.has_independent_dataset()


def test_no_null_test_means_no_claim():
    p = EvidenceProfile("X", "Y", Regime.DISCOVERY, has_null_test=False)
    assert max_claim(p) is ClaimLevel.NONE


def test_observational_caps_at_association():
    p = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    assert max_claim(p) is ClaimLevel.ASSOCIATION
    assert "ASOCIADO" in compile_claim(p)


def test_causal_language_only_when_identifiable():
    led = IndependenceLedger()
    p = EvidenceProfile("X", "Y", Regime.CONFIRMATION, design=DESIGN_CAUSAL,
                        causal_identifiable=True, independence=led)
    assert max_claim(p) is ClaimLevel.CAUSAL_UNDER_ASSUMPTIONS
    # "causa" is allowed here
    assert scan_overclaims("X causa Y bajo supuestos", p) == []
    # but not in an observational profile
    obs = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    v = scan_overclaims("esto demuestra que X causa Y", obs)
    assert any("causal" in x.reason or "causa" in x.phrase for x in v)
    assert any("demostrar" in x.reason for x in v)


def test_discovery_word_is_always_forbidden():
    p = EvidenceProfile("X", "Y", Regime.CONFIRMATION, design=DESIGN_CAUSAL,
                        causal_identifiable=True)
    v = scan_overclaims("este descubrimiento cambia el campo", p)
    assert v and "descubrimiento" in v[0].reason.lower() or v


def test_replicated_claim_requires_confirmation_and_strong():
    led = IndependenceLedger()
    led.add(IndependenceLevel.OTHER_STAT_METHOD, "m", agreed=True)
    led.add(IndependenceLevel.OTHER_DATASET_COHORT, "cohorte B", agreed=True)
    p = EvidenceProfile("X", "Y", Regime.CONFIRMATION,
                        design=DESIGN_PREDICTIVE_EXTERNAL, independence=led)
    assert max_claim(p) is ClaimLevel.REPLICATED
    # same evidence but still in discovery regime → cannot claim replication
    p2 = EvidenceProfile("X", "Y", Regime.DISCOVERY,
                         design=DESIGN_PREDICTIVE_EXTERNAL, independence=led)
    assert max_claim(p2) is ClaimLevel.PREDICTION
