# Human-in-the-Loop Scientific Understanding Benchmark

Source: `benchmarks/human_understanding.py`. Uses REAL ACERO investigations to validate that
the engine measures understanding by performance and that the gate blocks a flawed report.
Validates the METHOD, not any specific human.

| Case | What the human must do | Result |
|---|---|---|
| 1 SINDy | distinguish fit from structure, explain the imposed library, catch "recovering an equation is a law" | concept reaches CONCEPTUALLY_UNDERSTOOD; misconception detected; novelty claim BLOCKED_FOR_LEARNING (needs transfer) |
| 2 Analogy (oscillator↔RLC) | map variables, know what's conserved, reject full physical equivalence | equivalence correctly rejected; NOT a false positive (negation-aware) |
| 3 Sunspots | distinguish periodicity from mechanism; 11.2yr does not prove the dynamo | pattern≠mechanism understood; the bad claim triggers the `mechanism_vs_pattern` misconception |
| 4 Adversarial gate | detect leakage, miscalibration, a causal claim, non-reproducibility, Codex-as-evidence | global gate BLOCKED (5 blockers); the human's detect-error answer scores 1.0 |
| Transfer | apply identifiability (oscillator) to logistic growth, unseen mapping | transfer passes; the wrong "K is uniquely determined" answer scores 0 and is flagged |
| Prediction | predict before the noise result is revealed | prediction locked after reveal; overconfidence detected |

## Run it
```bash
acero learn benchmark
```

## What it does NOT show
It does not prove a particular human understands anything; it exercises the measurement
machinery on real artifacts. Grading is deterministic and can miss nuance — see the honesty
note in `human_understanding_engine.md`.
