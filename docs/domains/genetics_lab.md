# Genetics Lab (RESTRICTED)

**Scope (computational only):** population genetics, gene expression, abstract regulatory
networks, statistical inference on public/synthetic data.

**FORBIDDEN (never implemented, and screened in requests):** pathogen design, virulence /
gain-of-function optimization, human germline editing, wet-lab protocols, harmful synthesis,
clinical recommendations, personal (re)identification.

**Models:** Hardy–Weinberg, selection/drift (Wright–Fisher), Hill regulation, differential
expression with multiple-testing correction.

**Benchmark (8):** Hardy–Weinberg, selection+drift, population-structure confounding (naive
correlation removed within-population), diff-expression (Bonferroni removes false hits),
synthetic regulatory network, Hill saturation, latent variable (correlation not direct
regulation), and a spurious association claimed causal — **BLOCKED**.

**Gate rules:** association_not_causal.

**Limitations:** idealized populations / abstract networks; observational data is not
intervention; any wet-lab validation or clinical interpretation needs collaboration.
