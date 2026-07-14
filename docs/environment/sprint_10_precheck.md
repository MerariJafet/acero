# Sprint 10 Precheck — Scientific Domain Labs + Inline Gate + Hybrid Grader

- **Branch:** `feature/acero-sprint-10-scientific-domain-labs` (from
  `feature/acero-human-understanding-engine` @ `e44b7af`).
- **Baseline:** `make verify` green — 428 tests, ruff + mypy clean.
- **Codex CLI:** on PATH and `~/.local/bin/codex` (used real for adversarial audits).
- **Docker sandbox:** `acero-sandbox:py312` available; executable domain tasks reuse it.

## Existing pieces inspected
- `domains/` — 4 plugins (physics/astronomy/genetics/chemistry) with simulators,
  validation, known-answer benchmarks, and a `PolicyGuard`-checked registry.
- `epistemic_gate/` — 81 rules, 11 stages; `GlobalGate.check` reports but does NOT block
  a mutation. Codex advisory; policy bridge.
- `understanding/grading/` did not exist; grading was a single deterministic module
  (`assessment/grading.py`) with a keyword-echo guard.

## Write paths that currently BYPASS the gate (to protect)
- `world_model/graph.py`: `add_node`, `update_belief`, `update_node_data`, `link`,
  `reweight_edge`.
- `discovery/store.py`: `put`, `set_status`, `update_payload`.
- `understanding/store.py`: `save_*` (state, misconception, evidence, prediction).
- `ledger/service.py`: `create_project`, entity create/update.

## Approach
- **Inline gate:** an `enforce()` barrier that runs the gate BEFORE the mutation and,
  on block, records a separate rejection event and performs NO mutation. Guarded wrappers
  (`GatedWorldModel`) plus a thread-local gate context so a raw protected mutation invoked
  outside a gate transaction raises `BypassDetected` (opt-in flag, off by default so legacy
  paths keep working; guarded wrappers turn it on). Architectural bypass test.
- **Domain labs:** a `ScientificDomain` contract in `domains/core/` layered over the
  existing plugins; per-domain concepts, term libraries, benchmarks, gate rules, result
  classification, applicability limits.
- **Hybrid grader:** deterministic authority + Codex semantic advisory (never certifies) +
  contradiction/consistency + aggregation policy + calibration fixtures + adversarial audit.
