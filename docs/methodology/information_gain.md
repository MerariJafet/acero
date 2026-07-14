# Information Gain & Research Utility (Sprint 6)

Source: `discovery/information_gain.py`, `research_utility.py`,
`experiment_design.py`, `stopping.py`.

## Discriminating experiments
An experiment is only worth running if it can distinguish the hypotheses. We build
an **Experiment × Hypothesis × Expected-Outcome** matrix
(`ExperimentProposal.preregistered_predictions`). `require_discriminating` rejects
a proposal where every hypothesis predicts the same outcome. Groups of hypotheses
that share an outcome (and so won't be distinguished) are surfaced, not hidden.

## Expected Information Gain
When a probabilistic model exists:

    EIG = H(prior) - E_outcome[ H(posterior | outcome) ]

over hypotheses, with the posterior from Bayes' rule (`bayesian_eig`). Perfect
discrimination of two hypotheses yields exactly 1 bit. When probabilities are not
justified, a **documented heuristic** (`heuristic_eig`) returns an upper bound of
`log2(distinct_outcomes)` and says so. Priors may be uniform, human, or model-
suggested; `prior_sensitivity` reports how EIG varies across priors.

## Research utility (transparent multiobjective)
`compute_utility` returns `weighted_benefit / (1 + weighted_cost)` and **exposes
every part**: components (information_gain, scientific_value, falsification_power,
reproducibility, human_learning_value, compute/time/monetary cost, risk), weights,
benefit, cost. `weight_sensitivity` reports whether the top choice is stable across
weight variants. Costs/risks are normalised heuristics in [0,1], not currency.

## Stopping rules
`evaluate(DiscoveryState)` returns an explicit decision —
`CONTINUE | REFINE | PAUSE | STOP | ESCALATE_TO_HUMAN` — from auditable conditions
(budget exhausted, negligible improvement, a dominant hypothesis, repeated
inconclusive rounds, high prior sensitivity, missing data, no discriminating
experiment, risk > benefit). No silent infinite loops.

## Critics
A **mandatory** rule-based critic blocks experiments missing baseline, controls,
metrics, preregistration, or discrimination. An **advisory** Codex critic adds
subtle concerns (confounds, leakage, post-hoc selection) but is never blocking.
