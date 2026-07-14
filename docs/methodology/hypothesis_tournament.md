# Hypothesis Tournament (Sprint 5)

Source: `discovery/generation.py`, `diversity.py`, `falsifiability.py`,
`tournament.py`.

## Generation
`complete_json` with a strict schema forces Codex to return several **competing**
hypotheses (distinct mechanisms, not cosmetic variants), each with mechanism,
assumptions, predictions, falsification conditions, and required variables. A
deterministic `MockHypothesisGenerator` provides the same shape offline. Every
candidate records generation provenance (provider, model, prompt version, params,
token usage). LLM-claimed sources are stored as **unverified** and never become
evidence. A real Codex run produced e.g. NULL / MATHEMATICAL-exponential /
MECHANISTIC-power-law / COMPUTATIONAL-nonparametric — genuinely diverse.

## Hypothesis types
`DESCRIPTIVE, PREDICTIVE, MECHANISTIC, CAUSAL, MATHEMATICAL, COMPUTATIONAL,
ANALOGICAL, NULL, BASELINE, BOUNDARY_CASE`. Every investigation includes at least
a null/baseline, a motivated mechanism, an alternative, and a flexible (overfit-
prone) model.

## Falsifiability (heuristic, deterministic)
`falsifiability_score, actionability_score, specificity_score, assumption_burden`
∈ [0,1], derived from structural features (concrete predictions? explicit
falsification conditions? measurable variables? hedging language?). Documented as
heuristics, not universal measures.

## Diversity (rules + lexical, no embeddings)
Token-Jaccard similarity + structural rules classify each pair as duplicate /
paraphrase / shared_mechanism / param_only / distinct. Metrics: semantic
diversity, mechanism diversity, prediction diversity, assumption coverage, and the
**effective number of hypotheses** (exp of Shannon entropy over mechanism clusters).

## Tournament (multiobjective + Elo)
No single opaque score. Each candidate gets a transparent objective vector
(falsifiability, actionability, specificity, low-assumption-burden, diversity
contribution, feasibility, novelty). A deterministic round-robin (higher weighted
score wins each pair) feeds an Elo rating; **every pairwise comparison is retained**.
Final ranking = weighted multiobjective score, Elo tie-break. Codex may critique
(advisory); the ranking itself is rule-based and reproducible.

## Rejected hypotheses
Never deleted. Each records reason, evaluator, scores, and `reconsider_if`
conditions, and is preserved in the `discovery` store with status `REJECTED`.

## Known limitation
The default weights reward assumption-free hypotheses, so strong baselines can
rank highly. This is intentional (baselines are the thing to beat) but the weights
are configurable and their sensitivity is reported.
