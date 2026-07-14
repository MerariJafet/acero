# The Mandatory Epistemic Gate (Sprint 8.9)

Source: `inference/audit/gate.py`. A candidate CANNOT reach HUMAN_REVIEW if it fails
any critical deterministic check. Codex is an ADVISORY auditor: a Codex finding
becomes a blocker only when it names an existing rule (or a human promotes it).

## Deterministic blocker rules
invalid_dimensions, missing_provenance, data_leakage, no_baseline, no_controls,
not_reproducible, harking (predictions after results), negative_result_deleted,
non_identifiable_presented_as_unique, undeclared_miscalibration,
extrapolation_without_test, causal_claim_without_evidence, equivalent_counted_as_new,
codex_as_evidence.

## Statuses
`PASS` · `PASS_WITH_WARNINGS` · `BLOCKED` · `ESCALATE_TO_HUMAN`.
A fitting-only inference level raises a warning (do not call it a law). Data-insufficient
identifiability escalates to a human.

## Codex promotion
`evaluate(gi, codex_findings=[...])`: a finding with `rule` in the blocker set becomes a
blocker; any other Codex concern is recorded as a warning only. This keeps Codex
advisory while letting verifiable findings enforce the rules.

Tests: `tests/unit/test_inference_gate.py` (every rule), `tests/property/test_inference_properties.py`.
