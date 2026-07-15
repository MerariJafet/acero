# Human Scientific Review Gauntlet

Source: `benchmarks/review_gauntlet.py`. Six cases; all pass.

| Case | Expectation |
|---|---|
| 1 not reviewed | export BLOCKED |
| 2 not ready | export BLOCKED (readiness below ceiling) |
| 3 no comprehension | export BLOCKED |
| 4 AI reviewer | approval refused AND export blocked |
| 5 unresolved contradiction | export BLOCKED |
| 6 approved local export | writes LOCALLY; auto_published always False |

```bash
acero publication gauntlet
acero publication dossier
acero publication export --reviewer <you>   # gated local export; never publishes
```
