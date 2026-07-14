# Global Epistemic Gate (Sprint 9)

A transversal, mandatory layer governing the whole pipeline:

    Literature → Question → Hypotheses → Experiment Design → Execution → Inference
    → Cognitive (Analogy / Derivation) → World Model → Human Review → Publication

No result becomes accepted knowledge without passing the gate for its stage.

## Package `src/acero/epistemic_gate/`
- **models.py** — `Stage`, `Severity`, `GateOutcome` (PASS / PASS_WITH_WARNINGS / BLOCKED /
  ESCALATE_TO_HUMAN / BLOCKED_FOR_LEARNING), `GateRule` (id, stage, severity, checker,
  inputs, remediation, source, version), `GateResult`.
- **rules/** — deterministic checkers per stage (`literature`, `hypothesis`, `experiment`,
  `execution`, `inference`, `cognitive` [analogy + derivation], `world_model`,
  `understanding` [human review], `publication`). **81 rules total.**
- **registry.py** — central, versioned store; `promote_codex_finding` refuses to create a
  rule without a callable checker AND a regression test.
- **engine.py** — runs a stage's rules, computes the outcome, and walks the pipeline,
  stopping knowledge flow at the first BLOCKED stage.
- **reports.py**, **policy_bridge.py** (maps cost/publication/safety/autonomy policy
  violations into gate results — no duplicated rules), **audit.py** (self-audit).

## Two disciplines carried from the inference gate
1. **Missing input ≠ pass.** A rule whose declared input is absent raises `NotEvaluable`
   and is recorded as a *cannot-evaluate warning* — the gate never pretends to have checked
   something it couldn't.
2. **Codex is advisory.** A Codex finding raises only a warning unless it names an existing
   rule id (then it is promoted to that rule's blocker). Codex can never approve, block by
   itself, certify comprehension, or update a belief.

The inference stage GENERALIZES the Sprint 8.9 gate's 14 rules; `artifact_from_gate_input`
maps a `GateInput` onto the flat artifact the rules read, so the two never disagree.
