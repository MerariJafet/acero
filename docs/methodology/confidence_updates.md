# Confidence Updates (Sprint 7)

Source: `discovery/confidence.py`.

Two clearly-separated modes; the choice is explicit and recorded.

## Bayesian update (only when justified)
`bayesian_update(prior, likelihood)` with `posterior[h] ∝ prior[h] · P(observed |
h)`. Used only when genuine likelihoods exist. An uninformative observation leaves
the prior unchanged. The result is a normalised distribution.

## Ordinal update (default when probabilities aren't warranted)
`ordinal_update` moves a hypothesis along a labelled scale
`REFUTED < WEAKENED < NEUTRAL < SUPPORTED < STRONGLY_SUPPORTED`. It is explicitly
**ordinal**, never dressed up as a probability. Low-quality or non-reproducible
results move confidence **less** (or not at all): `assess_result_quality` gates the
step size on whether the run was OK, reproduced, and discriminating.

## No false precision
An LLM's stated confidence is never accepted as a scientific probability. In the
Hidden Dynamics benchmark the posterior is computed from a **temperature-tempered**
out-of-sample-RMSE likelihood and reported as *relative plausibility
(UNCALIBRATED)* — an adversarial-audit fix that removed an earlier overconfident
0.99 posterior. Calibration (reliability curves, coverage) is documented as future
work (Sprint 11).

## Which hypotheses weaken
`which_weakens` returns the hypotheses below the mean plausibility; these are
recorded as negative context in the Negative Results Registry (never deleted).
