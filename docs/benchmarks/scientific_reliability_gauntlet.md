# Scientific Reliability Gauntlet

Source: `benchmarks/reliability_gauntlet.py`. Ten end-to-end tracks; all pass.

| Track | Expectation |
|---|---|
| 1 clean pipeline | passes with minimal warnings |
| 2 duplicate evidence | 3 same-dataset results counted as dependent (1 effective) |
| 3 faulty solver | unstable-solver false evidence BLOCKED |
| 4 equivalent models | equivalent expressions detected, not counted as distinct |
| 5 contaminated literature | fake/retracted citation BLOCKED |
| 6 false causality | association-as-causal BLOCKED |
| 7 grader gaming | keyword echo / injection FAILS |
| 8 miscalibration | overconfident predictions detected (ECE high) |
| 9 correct abstention | data-insufficient → ESCALATE_TO_HUMAN |
| 10 concurrent bypass | 8 thread mutations without context all BLOCKED |

```bash
acero reliability gauntlet
```

A result surviving one execution is NOT the same as surviving an audit — that is what this
measures.
