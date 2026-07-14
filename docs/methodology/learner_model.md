# Methodology — Learner Model

## Knowledge states
`UNKNOWN → EXPOSED → RECOGNIZED → PARTIALLY_UNDERSTOOD → PROCEDURALLY_COMPETENT →
CONCEPTUALLY_UNDERSTOOD → TRANSFER_CAPABLE → MASTERED`, plus off-ladder `MISCONCEIVED` and
`DECAYED`. Each rung is earned by a specific KIND of performance evidence (see
`learner/knowledge_state.py::STATE_EVIDENCE`). Advancement is at most one rung per piece of
evidence (except the initial UNKNOWN→EXPOSED exposure step). `MASTERED` additionally
requires ≥4 distinct evidence kinds.

## Confidence: self-reported vs observed
`confidence_observed` tracks demonstrated ability across dimensions (conceptual /
procedural / mathematical / transfer). `confidence_self_reported` is recorded but never
advances state. `overconfidence_gap = max(0, self − observed)`; human calibration
(`learner/confidence.py`) uses Brier score and reliability over several predictions to label
overconfident / underconfident / calibrated / insufficient.

## Forgetting and review
`history.next_review` shortens the interval for critical, error-prone, unused, or
overconfident concepts and lengthens it for recently-used, higher-mastery ones. Past the
review date with no new evidence, a concept is DECAYED.
