# Experiment Search, Tree & Scheduler (Sprint 7)

Source: `discovery/tree.py`, `scheduler.py`, `search.py`.

## Research tree
`Question → Hypotheses → Experiments`, persisted via `DiscoveryStore` so it
survives a restart. Each node records status, cost, priority, dependency, result,
information gain, decision, children, and the **reason it was expanded or pruned**.
States: `PROPOSED, VALIDATED, QUEUED, RUNNING, COMPLETED, FAILED, INCONCLUSIVE,
PRUNED, CANCELLED, RETRYABLE`. Pruning is explainable and recorded as a PRUNE
provenance event.

## Local scheduler
`LocalScheduler` is an in-process queue with: concurrency limit (ThreadPool),
per-task wall-clock timeout, retries with a budget, priority ordering,
cancellation (cooperative via a `stop` event), an `on_state` callback for
checkpointing, and **partial-failure isolation** (one task failing never kills the
batch). `run(tasks, skip_ids=...)` supports **resume**: already-completed tasks are
skipped. No distributed infrastructure; the sandbox enforces hard process timeouts.

## Search strategies
Implemented: `grid_search`, `random_search` (seeded, deterministic),
`adaptive_search` (local search around the best config), and `prune_by_score`
(keep top-k, explainable). Interfaces (`BayesianOptimizer`, `EvolutionarySearch`,
`ActiveLearner`) are declared for future work — no heavy dependencies added yet.

## Next best experiment
`recommend_next` picks the highest-utility experiment and **always** returns at
least one alternative plus an explicit `reason_not_to_run`.
