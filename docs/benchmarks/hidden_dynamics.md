# Hidden Dynamics Discovery Benchmark

Source: `benchmarks/hidden_dynamics.py`, `hidden_dynamics_script.py`. This is the
integration test for Sprints 5–7: ACERO receives noisy observations of a **hidden**
dynamical system and must find the model family that explains and extrapolates them.

## Systems
`exponential_decay`, `damped_oscillator`, `logistic`, `predator_prey`,
`chaotic_map`. The generating equation is hidden from the fitter. Data are split
into train/val/test (disjoint) plus an **extrapolation** region beyond the training
range.

## Competing model families (fitted in the sandbox)
`mean` (baseline), `linear`, `cubic`, `exponential`, `poly9` (flexible), plus
`damped` and `logistic` where relevant. Each is scored by RMSE on every split and
labelled by its extrapolation behaviour (monotonic / oscillatory / saturating /
diverging / flat) for discrimination.

## Loop (phases A–H)
Generate competing hypotheses → falsifiability filter → tournament → discriminating
extrapolation experiment → EIG + prior sensitivity → research tree → scheduler runs
seeds → determine winner → **Bayesian confidence update** → falsify the winner under
high noise → preserve negatives (poly9 overfit, weakened hypotheses) →
reproducibility check → next experiment → learning docs.

## Result (exponential_decay, seeds 1–2)
- Correct model recovery: winner = `exponential` = hidden family.
- poly9 extrapolation RMSE ≫ winner's (overfitting caught, kept as a negative result).
- EIG ≈ 0.77 bits; reproduced bit-for-bit.
- Posterior is tempered relative plausibility (max < 0.99), not a probability.

## Honesty conditions (always in the report)
- Data are synthetic with a known ground truth.
- This evaluates **model recovery**, not scientific discovery.
- The winning family is **structurally privileged** (data generated from it).
- The experimental base is small (few seeds/noise levels); no robust calibration
  claims.
- A simulation proves nothing about the physical world.

## Adversarial audit
`benchmarks/audit.py` runs a deterministic rules audit and an advisory Codex audit.
A real Codex audit produced 18 findings; verifiable ones were fixed (posterior
overconfidence → tempered; privileged-hypothesis disclosure; ranking/title order;
partial-ambiguity surfaced; `process_quality` relabelled; weakened hypotheses
recorded as negatives) with regression tests.

## Real data (documented, gated)
Extending to a small, licensed public time series is supported by the pipeline
(noise, missing values, units, provenance, uncertainty) but is **gated by policy**
(`data_access.yaml`) and makes no new domain claims. Not enabled by default.

## Run it
```bash
acero benchmark hidden-dynamics --system exponential_decay
acero benchmark hidden-dynamics --system damped_oscillator --sandbox docker
acero benchmark hidden-dynamics --llm      # Codex generation + critique (slow, costs tokens)
```
