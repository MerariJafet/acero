# The World Model Engine (Sprint 8)

The World Model is ACERO's living, persistent model of scientific knowledge. It is
NOT a graph of papers or files — it is a graph of **beliefs** and typed **relations**
that *changes* with every investigation. Source: `src/acero/world_model/`.

## Everything is a belief
No absolute truths. Every belief-bearing node (Claim, Hypothesis, Model, Law,
Theory, Prediction, Assumption, Equation, Constraint, Phenomenon) carries a
`BeliefState`: confidence, evidence_strength, counter_strength, replication_count,
negative_results, contradictions, open_questions, distinct_sources, last_update, and
a versioned **history**. Confidence is *derived* from these by a configurable
`BeliefPolicy` (smoothed base, replication bonus, contradiction/negative/single-
source penalties, `max_confidence < 1.0`) — no universal formula, and it can never
reach certainty.

## Node & relation types
30 node types (`nodes.py::NodeType`): Concept, Claim, Evidence, CounterEvidence,
Hypothesis, Prediction, Model, Experiment, Dataset, Variable, Parameter, Equation,
Law, Theory, Observation, Measurement, Method, Simulation, Assumption, Constraint,
Question, Contradiction, NegativeResult, Anomaly, OpenProblem, ResearchProgram,
Tool, Publication, Researcher, Domain, Phenomenon.
22 relation types (`edges.py::EdgeType`): supports, contradicts, depends_on,
generated_by, tests, explains, predicts, derived_from, refines, generalizes,
specializes, invalidates, requires, belongs_to, measured_by, computed_by,
observed_in, related_to, caused_by, hypothesizes, extends, replaces.

## The graph changes (it does not overwrite)
`WorldModel` (graph.py) persists nodes/edges (SQLite tables `world_nodes`,
`world_edges`, `world_node_history`). Beliefs are **updated, versioned, and
provenance-logged**; relations are **weakened (deactivated), not deleted**; `link`
is idempotent (no redundant edges). After each investigation
(`update.integrate_hidden_dynamics`) support goes up for the winner, down for the
overfitter (whose `explains` relation is weakened), and every competitor's belief is
updated from its fit.

## Contradictions & anomalies
`contradictions.detect_contradictions` finds incompatible beliefs (same subject,
incompatible stance), creates a Contradiction node, **opens a new Question**, and
penalises both beliefs. `anomalies.register_anomaly` records expected vs observed,
turns candidate explanations into hypotheses, opens an OpenProblem, and **never
deletes** the anomaly until resolved.

## Scientific memory
`queries.ScientificMemory` answers: which experiments support X? what contradicts it?
which hypotheses arose? which models depend on this (untested) assumption? what
failed? which anomalies are open? which beliefs were never tested? which relations
are weak? which claims rest on a single source?

## Programs, evolution, narration
`ResearchProgram` nodes group long-lived work. `evolution.evolution_report` reports
what we now believe more/less/the same, new contradictions/anomalies, and what to
research next. `narrate.narrate` emits the sentences a scientist would say
("this hypothesis gained support because N independent experiments favoured it";
"this theory depends critically on an untested assumption"; "the next experiment
has the highest value because it bears on M models in open contradictions").

## Visualization
`viz.render_html` writes a self-contained, offline HTML: nodes in columns by type,
coloured by confidence, sized by degree; red edges for contradicts/invalidates,
dashed for weakened; panels for open contradictions, anomalies, critical untested
assumptions, single-source claims, and weak relations.

## Real data
`ingest.ingest_exoplanets` folds the NASA Exoplanet Archive (P, a, M) into the graph
and tests Kepler's third law on ~2,900 real planets (slope≈1.0, R²≈0.999), moving
the law's belief from the prior toward supported — verifying the model changes
correctly with real data (not a discovery). See `docs/benchmarks/kepler_exoplanets.md`.

## Known limitations (from the adversarial audit)
Deeper items are documented, not yet built: normalised competing-posterior belief
state across models, richer temporal/versioned ontology surfaced in stats, deeper
`derived_from` chains, and question→experiment (`motivates`) edges. See ADR-0005 and
the Sprint 8 report.
