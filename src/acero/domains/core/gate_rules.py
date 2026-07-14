"""Domain-specific epistemic gate rules.

These enforce that a computational result is not dressed up as an experimental validation,
that a statistical association is not sold as causality, and that conservation laws
(mass/charge/stoichiometry) hold. They are exposed as checkers usable by the Global
Epistemic Gate INFERENCE stage over a domain-result artifact.
"""

from __future__ import annotations

from typing import Any

from .contracts import DomainResult, DomainResultClass


def simulation_not_physical(artifact: dict[str, Any]) -> str | None:
    """A simulation/model_fit must not be *claimed* as an experimental validation."""
    produced = artifact.get("result_class")
    claimed = artifact.get("claimed_class")
    if claimed in {DomainResultClass.PHYSICAL_VALIDATION.value,
                   DomainResultClass.BIOLOGICAL_VALIDATION.value,
                   DomainResultClass.CHEMICAL_VALIDATION.value} and produced != claimed:
        return (f"a {produced} is presented as {claimed} — computation is not "
                f"experimental validation")
    return None


def association_not_causal(artifact: dict[str, Any]) -> str | None:
    if (artifact.get("result_class") == DomainResultClass.STATISTICAL_ASSOCIATION.value
            and artifact.get("claims_causal")):
        return "a statistical association is presented as a causal claim"
    return None


def mass_conserved(artifact: dict[str, Any]) -> str | None:
    if artifact.get("mass_balanced") is False:
        return "reaction violates conservation of mass"
    return None


def stoichiometry_ok(artifact: dict[str, Any]) -> str | None:
    if artifact.get("stoichiometry_valid") is False:
        return "prediction violates stoichiometry"
    return None


def units_consistent(artifact: dict[str, Any]) -> str | None:
    if artifact.get("units_consistent") is False:
        return "dimensionally inconsistent domain result"
    return None


def solver_stable(artifact: dict[str, Any]) -> str | None:
    if artifact.get("solver_stable") is False:
        return "unstable solver — the numerical result is not trustworthy (false evidence)"
    return None


# name -> checker; domains reference these ids in their gate_rule_ids.
DOMAIN_CHECKERS = {
    "domain.simulation_not_physical_validation": simulation_not_physical,
    "domain.association_not_causal": association_not_causal,
    "domain.mass_conserved": mass_conserved,
    "domain.stoichiometry_respected": stoichiometry_ok,
    "domain.units_consistent": units_consistent,
    "domain.solver_stable": solver_stable,
}


def validate_domain_result(result: DomainResult, *, claimed_class: str | None = None,
                           claims_causal: bool = False, mass_balanced: bool | None = None,
                           stoichiometry_valid: bool | None = None,
                           units_consistent_flag: bool | None = None,
                           solver_stable_flag: bool | None = None) -> list[str]:
    """Run all applicable domain checkers; return a list of violation messages."""
    art: dict[str, Any] = {
        "result_class": result.result_class.value,
        "claimed_class": claimed_class or result.result_class.value,
        "claims_causal": claims_causal, "mass_balanced": mass_balanced,
        "stoichiometry_valid": stoichiometry_valid,
        "units_consistent": units_consistent_flag, "solver_stable": solver_stable_flag,
    }
    out: list[str] = []
    for checker in DOMAIN_CHECKERS.values():
        msg = checker(art)
        if msg:
            out.append(msg)
    return out
