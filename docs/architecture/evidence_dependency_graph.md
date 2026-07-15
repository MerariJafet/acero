# Evidence Dependency Graph (Sprint 11)

Two pieces of evidence are NOT independent when they share a dataset, sample, pipeline/code,
simulator, generating model, derived source, systematic error, or human analyst/method.
Types: `INDEPENDENT`, `SAME_DATASET`, `SAME_SAMPLE`, `SAME_PIPELINE`, `SAME_SIMULATOR`,
`DERIVED_SOURCE`, `SHARED_SYSTEMATIC`, `UNKNOWN_DEPENDENCY`.

`classify_pair` returns the strongest match; `DependencyGraph.clusters()` union-finds
dependent items so each cluster ≈ one effective sample. `dependency_aware_support` shows the
naive support (N·per-item) vs the honest support (clusters·per-item) and the inflation
avoided. Dependent evidence is never counted as independent replication; confidence never
reaches 1.
