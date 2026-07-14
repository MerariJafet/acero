# Methodology — Global Gate Rules

81 deterministic rules across the pipeline stages. Each rule declares its inputs, a
checker, a severity (blocker / warning / info), a remediation, a source, and a version.

| Stage | Rules (examples) |
|---|---|
| LITERATURE | citation exists, fragment supports claim, retraction respected, no duplicate-as-independent |
| HYPOTHESIS | has prediction, falsifiable, no duplicate alternative, novelty searched |
| EXPERIMENT_DESIGN | baseline, controls, prespecified metrics, discriminating, budget, stopping rule, confounders |
| EXECUTION | ran in sandbox, no secrets, authorized network, environment/seeds/hashes recorded, timeout, reproducible |
| INFERENCE | (generalizes the 14 Sprint-8.9 rules) dimensions, leakage, identifiability, equivalence, extrapolation, false precision, causal evidence, imposed structure declared, Codex-as-evidence, calibration, provenance, reproducible |
| ANALOGY | surface analogy not transferred, units compatible, broken structure declared, transfer tested, regime of validity |
| DERIVATION | valid symbolic steps, units, no hidden assumption, unresolved≠done, dim-analysis≠derivation, symmetry≠proof |
| WORLD_MODEL_UPDATE | not Codex-only, evidence provenance, contradiction not ignored, no overwrite, confidence<1, independent replication, simulation≠physical |
| HUMAN_REVIEW | minimum comprehension, critical concepts assessed, no active blocking misconception, human prediction, limitations reviewed, explicit approval |
| PUBLICATION | no AI authorship, citations verified, reproducible, methodology complete, data/code present, AI use declared, novelty not exaggerated, discovery human-reviewed, central conclusion understood |

## Disciplines
- **Missing input → cannot-evaluate warning**, never a silent pass.
- **Codex advisory** → warning unless it names a real rule; promotion into a rule requires a
  checker AND a test.
- **Policies bridged, not duplicated**: cost/publication/safety/autonomy violations surface
  as gate results via `policy_bridge.py`.
