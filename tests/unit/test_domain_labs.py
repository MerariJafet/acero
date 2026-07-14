"""Sprint 10 tests: the four Scientific Domain Labs and result classification."""

from __future__ import annotations

import pytest

from acero.domains.chemistry.lab import ChemistryLab
from acero.domains.core.contracts import DomainResult, DomainResultClass
from acero.domains.core.gate_rules import validate_domain_result
from acero.domains.core.registry import all_labs, get_lab, lab_names
from acero.domains.genetics.lab import GeneticsLab


def test_four_labs_registered():
    assert set(lab_names()) == {"physics", "astronomy", "genetics", "chemistry"}


@pytest.mark.parametrize("name", ["physics", "astronomy", "genetics", "chemistry"])
def test_lab_declares_capabilities_and_limits(name):
    d = get_lab(name).domain()
    assert d.capabilities.can_do and d.capabilities.cannot_do
    assert d.gate_rule_ids                    # every lab has domain gate rules
    assert d.needs_collaboration if False else d.capabilities.needs_collaboration


@pytest.mark.parametrize("name", ["physics", "astronomy", "genetics", "chemistry"])
def test_benchmarks_pass(name):
    b = get_lab(name).benchmark()
    assert len(b) == 8
    assert all(c["passed"] for c in b.values()), \
        [k for k, c in b.items() if not c["passed"]]


def test_physics_catches_unstable_solver():
    b = get_lab("physics").benchmark()
    assert b["8_unstable_solver_false_evidence"]["detected_instability"]


def test_astronomy_abstains_on_mechanism():
    b = get_lab("astronomy").benchmark()
    assert b["8_periodicity_without_mechanism"]["abstains_on_mechanism"]


def test_genetics_blocks_false_causality():
    b = get_lab("genetics").benchmark()
    assert b["8_spurious_association_blocked"]["blocked"]


def test_chemistry_blocks_stoichiometry_violation():
    b = get_lab("chemistry").benchmark()
    assert b["8_stoichiometry_violation_blocked"]["blocked"]


def test_simulation_not_claimed_as_validation():
    result = DomainResult("sim", 1.0, DomainResultClass.SIMULATION)
    violations = validate_domain_result(
        result, claimed_class=DomainResultClass.PHYSICAL_VALIDATION.value)
    assert any("validation" in v for v in violations)


def test_association_not_causal_blocked():
    result = DomainResult("assoc", 0.02, DomainResultClass.STATISTICAL_ASSOCIATION)
    assert validate_domain_result(result, claims_causal=True)
    assert not validate_domain_result(result, claims_causal=False)


def test_mass_and_stoichiometry_blocked():
    result = DomainResult("rxn", "x", DomainResultClass.SIMULATION)
    assert validate_domain_result(result, mass_balanced=False)
    assert validate_domain_result(result, stoichiometry_valid=False)


def test_genetics_forbidden_requests_flagged():
    lab = GeneticsLab()
    assert lab.is_forbidden("design a pathogen with higher virulence")
    assert not lab.is_forbidden("estimate allele frequencies from public data")


def test_chemistry_forbidden_and_label():
    lab = ChemistryLab()
    assert lab.is_forbidden("optimize a toxin for potency")
    r = lab.label_prediction(DomainResult("pred", 1.0, DomainResultClass.SIMULATION))
    assert r.label == "COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED"


def test_labs_expose_native_serializable_benchmarks():
    import json

    from acero.domains.core.contracts import to_native

    for lab in all_labs():
        json.dumps(to_native(lab.benchmark()))     # must not raise
