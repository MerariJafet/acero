# The Discovery Engine (Sprints 5–7)

The Discovery Engine turns a scientific question into a *process* that reduces
uncertainty through reproducible experiments. It lives in `src/acero/discovery/`
and is exercised end-to-end by the Hidden Dynamics benchmark.

## Pipeline

```
question
  → generate competing hypotheses            (generation.py, mock | Codex)
    → filter falsifiable                      (falsifiability.py)
      → tournament (multiobjective + Elo)     (tournament.py, diversity.py)
        → keep top-k, REJECT rest (kept)      (supervisor.py, store.py)
          → discriminating experiment         (experiment_design.py)
            → rule critic (barrier) + Codex    (experiment_critic.py)
              → EIG + prior sensitivity        (information_gain.py)
                → research utility ranking     (research_utility.py)
                  → research tree              (tree.py)
                    → scheduler (concurrency)  (scheduler.py)
                      → sandboxed execution    (sandbox/*)
                        → confidence update    (confidence.py)
                          → falsify winner
                            → negatives kept   (negative_registry.py)
                              → next experiment (next_experiment.py)
                                → stopping rule (stopping.py)
```

Every step emits a `ProvenanceEvent` via `ResearchLedger.record_event`.

## Design rules (enforced, not aspirational)
- **Codex is never evidence.** All LLM output (generation, critics, audit) is
  advisory; the authoritative logic is deterministic and verifiable.
- **No hypothesis accepted for plausibility.** The tournament combines
  falsifiability, diversity, feasibility, novelty, and assumption burden — a
  transparent vector, not one opaque score.
- **No experiment without preregistration.** Predictions and the discrimination
  matrix are fixed before running; non-discriminating experiments are rejected.
- **Nothing deleted.** Rejected hypotheses and negative results are preserved
  (`DiscoveryStore.delete` refuses them).
- **No false precision.** Confidence is Bayesian only when justified, otherwise
  ordinal; the benchmark reports *relative plausibility (uncalibrated)*, never a
  calibrated probability.
- **All execution is sandboxed.** Tool creation and experiments run in the
  subprocess/Docker sandbox; nothing runs outside it.

## Persistence
`ledger/models.py::DiscoveryRow` (generic `discovery` table, discriminated by
`kind`: candidate | proposal | tree_node | tool | negative) with `status` and
`parent_id` columns for queryable state. `DiscoveryStore` mediates all writes and
emits provenance.

## Agents (as verifiable services, not prompts)
`DiscoverySupervisor` orchestrates generation → tournament → proposal → critique.
The hypothesis generator, experiment critic, and adversarial auditor have Codex
implementations behind `complete_json`; each has a deterministic/mock counterpart
so the whole engine runs offline for tests.
