"""Scientific Capability Evaluation Engine (Sprint 18).

Continuously measures whether ACERO is improving, degrading, or merely adding complexity. It
NEVER self-approves, never edits production without a gate, and never treats more tests/code as
scientific improvement. A capability's status is evidence-driven; regressions are declared only
against pre-registered thresholds vs a locked baseline.
"""
