# Governing Dynamics Inference Benchmark

Source: `benchmarks/governing_dynamics.py`. Seven levels validate the METHOD on
synthetic systems with the equation HIDDEN (not a discovery).

| Level | Test | Result |
|---|---|---|
| 1 Recovery | infer exp/logistic/damped/predator-prey | correct dominant terms recovered |
| 2 Noise | damped at noise 0 / 0.02 / 0.1 | R²(dv/dt) degrades 1.0 → 0.92 → 0.29 (honest) |
| 3 Omitted variable | predator-prey observing only x | structured residuals (autocorr≈1.0) → missing-variable flagged; variable NOT invented |
| 4 Equivalence | exp-decay vs slow-logistic (match early) | no winner declared; discriminating experiment picks the high-amplitude IC where they diverge |
| 5 Regime | decay rate changes at t=5 | regime change detected (no false positive on periodic data) |
| 6 Conservation | harmonic energy | invariant x²+v²/4 recovered, exact, survives noise |
| 7 Adversarial | wrong units + leakage + non-reproducible + equivalent-as-new + Codex-as-evidence + non-identifiable-as-unique | epistemic gate BLOCKED (8 blockers) |

## Honesty
Synthetic data; structure identified from an IMPOSED library; a fitted equation is NOT
a law; under noise/omitted-variable the system degrades or abstains rather than
inventing certainty.

## Run it
```bash
acero inference discover damped        # infer one system
acero inference benchmark              # all 7 levels
acero inference gate --bad             # see the gate block a flawed candidate
```
