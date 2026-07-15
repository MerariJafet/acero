# Methodology — Evidence Independence

Independent evidence weighs more; duplicated evidence must not inflate support. ACERO
fingerprints each evidence item (dataset, sample, pipeline, simulator, source paper, derived
source, systematic error, analyst, method) and collapses dependent items into clusters. A
meta-analysis over N items with M independent clusters is worth M, not N. Correlated human
judgement (same analyst/team/methodology) is a dependence too. See
`docs/architecture/evidence_dependency_graph.md`.
