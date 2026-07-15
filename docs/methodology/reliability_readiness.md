# Methodology — Reliability Readiness

The `ScientificReliabilityCard` reports each dimension (reproducibility, calibration,
evidence independence, adversarial robustness, numerical stability, domain validity, human
understanding, gate compliance, provenance completeness, unresolved contradictions,
abstention quality) with its measurement, sample, version, limitation, trend, and threshold.
There is no single magic trust score.

Readiness climbs `NOT_READY → EXPLORATORY → COMPUTATIONALLY_REPRODUCIBLE →
METHODOLOGICALLY_REVIEWED → ADVERSARIALLY_TESTED → EXTERNALLY_VALIDATED →
READY_FOR_HUMAN_SCIENTIFIC_REVIEW`. The ceiling means neither publication nor discovery —
`DISCOVERY_CONFIRMED` is intentionally not implemented. A `PublicationCandidate` prepares an
artifact for human review and can never publish automatically.
