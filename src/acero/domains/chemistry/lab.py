"""Chemistry Lab: kinetics, thermodynamics, molecular descriptors — computational only.

Permitted: kinetics, thermodynamics, public molecular properties, safe MD, educational
docking, small quantum chemistry, abstract reaction networks. FORBIDDEN (never
implemented): toxin/explosive/drug design, hazardous synthesis, scale-up, harmful lab
instructions. Every computational prediction is labelled
COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED. The gate blocks a stoichiometry
violation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.contracts import (
    Concept,
    DomainCapabilities,
    DomainLab,
    DomainModel,
    DomainResult,
    DomainResultClass,
    SafetyClass,
    ScientificDomain,
)

FORBIDDEN = ("toxin", "explosive", "nerve agent", "drug synthesis", "hazardous synthesis",
             "scale-up", "weaponi")
NOT_VALIDATED = "COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED"


class ChemistryLab(DomainLab):
    def domain(self) -> ScientificDomain:
        return ScientificDomain(
            id="chemistry", name="Computational Chemistry",
            ontology="chemical kinetics, thermodynamics, molecular descriptors, reaction "
                     "networks, mass/charge conservation",
            concepts=[
                Concept("rate", "speed of a reaction", ["k", "C"],
                        {"k": "1/s", "C": "mol/L"}),
                Concept("equilibrium", "forward = reverse rate", ["Keq"]),
                Concept("arrhenius", "temperature dependence of rate", ["Ea", "T"],
                        {"Ea": "J/mol", "T": "K"}),
                Concept("conservation", "mass and charge are conserved", []),
            ],
            units={"concentration": "mol/L", "rate_constant": "1/s", "T": "K",
                   "Ea": "J/mol"},
            dimensions={"rate": "mol/(L·s)"},
            scales={"molecular": "single reaction", "network": "coupled reactions"},
            supported_problem_types=["kinetics", "equilibrium", "arrhenius",
                                     "reaction-network", "descriptors"],
            models=[
                DomainModel("first_order", "d[A]/dt = -k[A]", ["well-mixed"], "dilute",
                            DomainResultClass.SIMULATION),
                DomainModel("michaelis_menten", "v = Vmax·S/(Km+S)", ["QSSA"], "enzyme",
                            DomainResultClass.MODEL_FIT),
                DomainModel("arrhenius", "k = A·exp(-Ea/RT)", ["single barrier"], "gas/liq",
                            DomainResultClass.CALCULATION),
            ],
            tools=["kinetics_integrator", "mass_balance_check", "arrhenius"],
            solvers=["ode-rk4", "stiff-implicit"],
            datasets=["synthetic kinetics", "public molecular properties"],
            validation_rules=["mass balance", "charge balance", "units", "stoichiometry",
                              "temperature range", "numerical stability"],
            gate_rule_ids=["domain.mass_conserved", "domain.stoichiometry_respected",
                           "domain.units_consistent"],
            safety_class=SafetyClass.RESTRICTED,
            capabilities=DomainCapabilities(
                can_do=["integrate kinetics", "fit Michaelis–Menten", "check conservation",
                        "Arrhenius scaling"],
                cannot_do=list(FORBIDDEN),
                approximations=["well-mixed", "QSSA", "single-barrier Arrhenius"],
                dependencies=["numpy"],
                risks=["a computational prediction is not experimental validation"],
                needs_collaboration=["any experimental validation / synthesis"]),
            learning_requirement_kind="")

    def classify(self, kind: str) -> DomainResultClass:
        return {"kinetics": DomainResultClass.SIMULATION,
                "fit": DomainResultClass.MODEL_FIT,
                "arrhenius": DomainResultClass.CALCULATION}.get(
                    kind, DomainResultClass.SIMULATION)

    def is_forbidden(self, request: str) -> bool:
        low = request.lower()
        return any(f in low for f in FORBIDDEN)

    def label_prediction(self, result: DomainResult) -> DomainResult:
        result.label = NOT_VALIDATED
        return result

    def benchmark(self) -> dict[str, Any]:
        return {
            "1_first_order_kinetics": self._first_order(),
            "2_reversible_reaction": self._reversible(),
            "3_michaelis_menten": self._michaelis_menten(),
            "4_arrhenius": self._arrhenius(),
            "5_mass_conservation": self._mass_conservation(),
            "6_stiff_system": self._stiff(),
            "7_nonidentifiable_parameter": self._nonidentifiable(),
            "8_stoichiometry_violation_blocked": self._stoichiometry_violation(),
        }

    def _first_order(self) -> dict[str, Any]:
        k = 0.5
        t = np.linspace(0, 10, 200)
        a = np.exp(-k * t)
        # half-life check
        thalf = np.log(2) / k
        return {"half_life": round(float(thalf), 3),
                "monotone_decay": bool(np.all(np.diff(a) < 0)),
                "passed": abs(a[np.argmin(abs(t - thalf))] - 0.5) < 0.05}

    def _reversible(self) -> dict[str, Any]:
        kf, kr = 1.0, 0.25
        a, b = 1.0, 0.0
        dt = 0.001
        for _ in range(20000):
            r = kf * a - kr * b
            a -= r * dt
            b += r * dt
        keq = b / a
        return {"Keq_expected": kf / kr, "Keq_reached": round(keq, 3),
                "passed": abs(keq - kf / kr) < 0.1}

    def _michaelis_menten(self) -> dict[str, Any]:
        vmax, km = 2.0, 0.5
        s = np.linspace(0, 10, 100)
        v = vmax * s / (km + s)
        return {"v_at_high_S": round(float(v[-1]), 3), "approaches_vmax": v[-1] > 0.9 * vmax,
                "passed": bool(v[-1] > 0.9 * vmax)}

    def _arrhenius(self) -> dict[str, Any]:
        a_pre, ea, r = 1e13, 80e3, 8.314
        t = np.array([300.0, 350.0, 400.0])
        k = a_pre * np.exp(-ea / (r * t))
        return {"k_increases_with_T": bool(np.all(np.diff(k) > 0)),
                "passed": bool(np.all(np.diff(k) > 0))}

    def _mass_conservation(self) -> dict[str, Any]:
        # A -> B, total should stay constant
        a, b = 1.0, 0.0
        k = 0.7
        dt = 0.001
        totals = []
        for _ in range(5000):
            r = k * a * dt
            a -= r
            b += r
            totals.append(a + b)
        drift = max(totals) - min(totals)
        return {"mass_drift": round(float(drift), 6), "passed": drift < 1e-6}

    def _stiff(self) -> dict[str, Any]:
        """A stiff system: explicit Euler with a large step goes unstable → flagged."""
        k_fast = 1000.0
        dt = 0.01                                          # too large for k_fast
        a = 1.0
        vals = []
        for _ in range(50):
            a = a - k_fast * a * dt
            vals.append(a)
        unstable = not np.all(np.isfinite(vals)) or max(abs(v) for v in vals) > 1e3
        return {"detected_stiffness": bool(unstable), "passed": bool(unstable)}

    def _nonidentifiable(self) -> dict[str, Any]:
        """Only the product k1·k2 is observable → the individual rates are not identifiable."""
        # observed steady flux depends on product; many (k1,k2) fit the same product
        product = 2.0
        pairs = [(1.0, 2.0), (2.0, 1.0), (0.5, 4.0)]
        same_flux = all(abs(k1 * k2 - product) < 1e-9 for k1, k2 in pairs)
        return {"identifiable": False, "observable": "k1*k2 only",
                "many_pairs_fit": same_flux, "passed": same_flux}

    def _stoichiometry_violation(self) -> dict[str, Any]:
        """A predicted reaction that violates stoichiometry → the gate must block."""
        from ..core.gate_rules import validate_domain_result

        result = DomainResult(kind="reaction_prediction", value="H2 + O2 -> H2O (unbalanced)",
                              result_class=DomainResultClass.SIMULATION,
                              label=NOT_VALIDATED)
        violations = validate_domain_result(result, mass_balanced=False,
                                            stoichiometry_valid=False)
        return {"violations": violations, "blocked": bool(violations),
                "passed": bool(violations)}
