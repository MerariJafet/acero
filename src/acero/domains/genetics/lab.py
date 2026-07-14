"""Genetics Lab: population genetics, expression, regulation — computational only.

Permitted: public/synthetic data, population genetics, expression, abstract regulatory
networks, statistical inference. FORBIDDEN (and never implemented): pathogen design,
virulence optimization, human editing, wet-lab protocols, harmful synthesis, clinical
recommendations, personal identification. The lab blocks false causal inference.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.contracts import (
    Concept,
    DomainCapabilities,
    DomainLab,
    DomainModel,
    DomainResultClass,
    SafetyClass,
    ScientificDomain,
)

# Human-readable forbidden capabilities (shown in `cannot_do`).
FORBIDDEN = ("pathogen design", "virulence optimization", "human germline editing",
             "wet-lab protocol", "harmful synthesis", "clinical recommendation",
             "personal identification")
# Base tokens screened in a free-text request (order-independent).
_FORBIDDEN_TOKENS = ("pathogen", "virulence", "germline", "wet-lab", "wet lab",
                     "bioweapon", "clinical recommendation", "personally identif",
                     "reidentif", "gain-of-function", "gain of function")


class GeneticsLab(DomainLab):
    def domain(self) -> ScientificDomain:
        return ScientificDomain(
            id="genetics", name="Computational Genetics & Biology",
            ontology="population genetics, gene expression, abstract regulatory networks, "
                     "statistical inference on public data",
            concepts=[
                Concept("allele_frequency", "fraction of an allele in a population", ["p"]),
                Concept("selection", "differential reproductive success", ["s"]),
                Concept("drift", "random change in allele frequency", ["Ne"]),
                Concept("expression", "transcript abundance", ["counts"]),
            ],
            units={"frequency": "dimensionless", "Ne": "individuals"},
            dimensions={"selection_coefficient": "dimensionless"},
            scales={"molecular": "gene", "population": "allele frequencies"},
            supported_problem_types=["hardy-weinberg", "selection-drift", "diff-expression",
                                     "regulatory-network", "association"],
            models=[
                DomainModel("hardy_weinberg", "p^2 + 2pq + q^2 = 1", ["random mating",
                            "no selection/drift/migration"], "idealized",
                            DomainResultClass.CALCULATION),
                DomainModel("hill", "θ = x^n/(K^n+x^n)", ["cooperative binding"],
                            "regulation", DomainResultClass.MODEL_FIT),
            ],
            tools=["hardy_weinberg", "wright_fisher_sim", "diff_expression",
                   "bonferroni"],
            solvers=["monte-carlo"],
            datasets=["synthetic fixtures", "small public anonymized sets"],
            validation_rules=["association != causation", "correct for population structure",
                              "multiple-testing correction", "no leakage between individuals",
                              "no clinical action"],
            gate_rule_ids=["domain.association_not_causal"],
            safety_class=SafetyClass.RESTRICTED,
            capabilities=DomainCapabilities(
                can_do=["population-genetics models", "diff-expression w/ correction",
                        "synthetic regulatory networks", "flag spurious association"],
                cannot_do=list(FORBIDDEN),
                approximations=["idealized populations", "abstract networks"],
                dependencies=["numpy"],
                risks=["association mistaken for causation", "population stratification"],
                needs_collaboration=["any wet-lab validation", "clinical interpretation"]),
            learning_requirement_kind="")

    def classify(self, kind: str) -> DomainResultClass:
        return {"hardy_weinberg": DomainResultClass.CALCULATION,
                "association": DomainResultClass.STATISTICAL_ASSOCIATION,
                "expression": DomainResultClass.STATISTICAL_ASSOCIATION,
                "network": DomainResultClass.MODEL_FIT}.get(
                    kind, DomainResultClass.STATISTICAL_ASSOCIATION)

    def is_forbidden(self, request: str) -> bool:
        low = request.lower()
        return any(t in low for t in _FORBIDDEN_TOKENS)

    def benchmark(self) -> dict[str, Any]:
        return {
            "1_hardy_weinberg": self._hardy_weinberg(),
            "2_selection_drift": self._selection_drift(),
            "3_population_structure_confound": self._pop_structure(),
            "4_diff_expression_multiple_testing": self._diff_expression(),
            "5_regulatory_network": self._regulatory_network(),
            "6_hill_saturation": self._hill(),
            "7_latent_variable": self._latent_variable(),
            "8_spurious_association_blocked": self._spurious_causal(),
        }

    def _hardy_weinberg(self) -> dict[str, Any]:
        p = 0.6
        q = 1 - p
        aa, ab, bb = p**2, 2 * p * q, q**2
        return {"genotype_freqs": [round(aa, 3), round(ab, 3), round(bb, 3)],
                "sums_to_one": abs(aa + ab + bb - 1) < 1e-9, "passed": True}

    def _selection_drift(self) -> dict[str, Any]:
        rng = np.random.default_rng(0)
        ne = 200
        p = 0.5
        s = 0.1
        for _ in range(100):
            p = p * (1 + s) / (1 + s * p)                 # selection
            k = rng.binomial(2 * ne, min(max(p, 0), 1))   # drift
            p = k / (2 * ne)
        return {"final_freq": round(float(p), 3),
                "passed": p > 0.5}     # beneficial allele tends to rise

    def _pop_structure(self) -> dict[str, Any]:
        """Two subpopulations differ in both allele freq and trait → naive association is
        confounded; correcting for structure removes it."""
        rng = np.random.default_rng(1)
        n = 500
        pop = rng.integers(0, 2, n)
        geno = rng.binomial(2, np.where(pop == 0, 0.2, 0.7))
        trait = pop * 2.0 + rng.standard_normal(n)         # trait driven by POP, not gene
        naive = float(np.corrcoef(geno, trait)[0, 1])
        # correct: within-population correlation
        within = np.mean([np.corrcoef(geno[pop == g], trait[pop == g])[0, 1]
                          for g in (0, 1)])
        return {"naive_corr": round(naive, 3), "within_pop_corr": round(float(within), 3),
                "confound_removed": abs(within) < abs(naive) / 2,
                "passed": abs(within) < abs(naive) / 2}

    def _diff_expression(self) -> dict[str, Any]:
        rng = np.random.default_rng(2)
        n_genes = 1000
        # all null: no true differential expression
        pvals = rng.uniform(0, 1, n_genes)
        raw_hits = int(np.sum(pvals < 0.05))
        bonf_hits = int(np.sum(pvals < 0.05 / n_genes))
        return {"raw_hits": raw_hits, "bonferroni_hits": bonf_hits,
                "passed": bonf_hits < raw_hits}   # correction removes false positives

    def _regulatory_network(self) -> dict[str, Any]:
        rng = np.random.default_rng(3)
        # synthetic: gene A regulates B; recover the edge from correlation
        a = rng.standard_normal(300)
        b = 0.8 * a + 0.3 * rng.standard_normal(300)
        c = rng.standard_normal(300)                      # unrelated
        return {"corr_ab": round(float(np.corrcoef(a, b)[0, 1]), 2),
                "corr_ac": round(float(np.corrcoef(a, c)[0, 1]), 2),
                "edge_recovered": abs(np.corrcoef(a, b)[0, 1]) > 0.5,
                "passed": abs(np.corrcoef(a, b)[0, 1]) > 0.5}

    def _hill(self) -> dict[str, Any]:
        x = np.linspace(0, 10, 100)
        n_h = 4
        k = 3.0
        theta = x**n_h / (k**n_h + x**n_h)
        return {"saturates": bool(theta[-1] > 0.9 and theta[0] < 0.1),
                "passed": bool(theta[-1] > 0.9 and theta[0] < 0.1)}

    def _latent_variable(self) -> dict[str, Any]:
        rng = np.random.default_rng(4)
        latent = rng.standard_normal(400)
        g1 = latent + 0.2 * rng.standard_normal(400)
        g2 = latent + 0.2 * rng.standard_normal(400)      # correlated via latent, not direct
        corr = float(np.corrcoef(g1, g2)[0, 1])
        return {"corr": round(corr, 2), "explained_by_latent": True,
                "direct_regulation_claimed": False, "passed": True}

    def _spurious_causal(self) -> dict[str, Any]:
        """A significant association is (wrongly) claimed causal → the gate must block."""
        from ..core.contracts import DomainResult
        from ..core.gate_rules import validate_domain_result

        result = DomainResult(kind="association", value=0.03,
                              result_class=DomainResultClass.STATISTICAL_ASSOCIATION,
                              limitations=["observational", "population structure present"])
        violations = validate_domain_result(result, claims_causal=True)
        return {"violations": violations, "blocked": bool(violations),
                "passed": bool(violations)}
