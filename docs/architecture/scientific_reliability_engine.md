# Scientific Reliability & Adversarial Assurance Engine (Sprint 11)

A transversal layer that does not add scientific capabilities — it checks which of the
existing ones deserve trust. It quantifies and declares SEPARATELY: the code working ≠ the
experiment being correct ≠ the result being reproducible ≠ the inference being calibrated ≠
the evidence being independent ≠ the conclusion being true ≠ the knowledge being ready to
publish.

## Package `src/acero/reliability/`
- **evidence.py** — evidence dependency graph (dataset/sample/pipeline/simulator/derived/
  systematic/analyst/method), clusters, dependency-aware support, replication levels,
  multidimensional `EvidenceQuality`.
- **calibration.py** — `CalibrationRegistry`: Brier/log-loss/ECE/MCE/reliability/sharpness/
  coverage/risk-coverage/abstention, kept separate by domain/task/difficulty/version;
  declares `INSUFFICIENT_CALIBRATION_DATA`.
- **recalibration.py** — binning / temperature scaling / interval inflation, fit on a
  CALIBRATION split, never on test; refuses overlapping splits (`LeakageError`).
- **red_team.py** — versioned adversarial case library wired to REAL detectors + runner.
- **mutation.py** — scientific mutation testing (units, baseline, control, prereg, dataset,
  source, negatives) — the gate must catch each.
- **domain_reliability.py** — refinement convergence, stability, multiple-testing,
  conservation per domain.
- **scorecard.py** — `ScientificReliabilityCard` (no single trust score), `ReadinessLevel`
  ladder (ceiling `READY_FOR_HUMAN_SCIENTIFIC_REVIEW`), `PublicationCandidate` (never
  auto-publishes).
- **engine.py** — orchestrates the probes into a card + readiness + candidate.

## Gauntlet
`benchmarks/reliability_gauntlet.py` — 10 end-to-end tracks (clean, duplicate evidence,
faulty solver, equivalent models, contaminated literature, false causality, grader gaming,
miscalibration, correct abstention, concurrent bypass). All pass.

## Honesty
Computational assessment only. Reproducible ≠ correct; independent ≠ true; calibrated ≠
validated. A result validated only in simulation is not experimentally validated.
`READY_FOR_HUMAN_SCIENTIFIC_REVIEW` is the ceiling and means neither publication nor
discovery — `DISCOVERY_CONFIRMED` is intentionally not implemented.
