"""CCC-1: pre-registration and the DISCOVERY/CONFIRMATION regime split (offline)."""

from __future__ import annotations

import pytest

from acero.science.preregistration import (
    FreezeError,
    FrozenAnalysisPlan,
    ProtocolRegistry,
    Regime,
    protocol_hash,
)


def _plan(**over) -> FrozenAnalysisPlan:
    base = dict(
        hypothesis="metilación de CpG X difiere entre casos y controles",
        primary_variable="beta_cpgX", population="cohorte Y adultos",
        inclusion_criteria="diagnóstico confirmado", exclusion_criteria="comorbilidad Z",
        variable_transform="M-value", statistical_model="limma + covariables",
        primary_test="t moderado", multiplicity_correction="BH-FDR",
        min_effect_size=0.05, decision_rule="FDR<0.05 y |Δ|>=0.05",
        failure_conditions="lambda_gc>1.2 o n_efectivo<100",
    )
    base.update(over)
    return FrozenAnalysisPlan(**base)


def test_hash_is_deterministic_and_content_only():
    p1 = _plan(author="a", created_at="2020-01-01T00:00:00Z")
    p2 = _plan(author="b", created_at="2999-12-31T00:00:00Z")
    # bookkeeping differs, science identical → same hash
    assert protocol_hash(p1) == protocol_hash(p2)
    # changing a scientific field changes the hash (post-hoc edits become visible)
    assert protocol_hash(_plan(min_effect_size=0.10)) != protocol_hash(p1)


def test_cannot_freeze_incomplete_plan():
    reg = ProtocolRegistry()
    with pytest.raises(FreezeError):
        reg.freeze(_plan(primary_test=""))


def test_freeze_is_idempotent():
    reg = ProtocolRegistry()
    a = reg.freeze(_plan())
    b = reg.freeze(_plan())
    assert a.hash == b.hash and reg.is_registered(a.hash)


def test_cannot_unblind_without_frozen_protocol():
    reg = ProtocolRegistry()
    h = protocol_hash(_plan())            # computed but NOT registered
    assert not reg.can_unblind(h)
    with pytest.raises(PermissionError):
        reg.unblind(h, dataset_ref="holdout_cohort_B")


def test_regime_is_discovery_until_unblinded_then_confirmation():
    reg = ProtocolRegistry()
    pre = reg.freeze(_plan())
    # frozen but not yet unblinded → still discovery (nothing confirmed)
    assert reg.classify(pre.hash) is Regime.DISCOVERY
    reg.unblind(pre.hash, dataset_ref="holdout_cohort_B")
    assert reg.classify(pre.hash) is Regime.CONFIRMATION
    # no protocol at all → discovery
    assert reg.classify(None) is Regime.DISCOVERY


def test_deviations_are_append_only_audit():
    reg = ProtocolRegistry()
    pre = reg.freeze(_plan())
    reg.record_deviation(pre.hash, "primary_test", "t moderado", "Wilcoxon",
                         "residuos no normales")
    devs = reg.deviations(pre.hash)
    assert len(devs) == 1 and devs[0].field_changed == "primary_test"
    # the frozen plan itself is unchanged (immutable) — deviation is external
    assert reg.get(pre.hash).plan.primary_test == "t moderado"
