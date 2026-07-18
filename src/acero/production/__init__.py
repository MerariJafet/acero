"""ACERO Production Readiness — scoring framework + improvement loop (Iteration 0+).

Provides an evidence-weighted 100-point rubric with hard rules that prevent a high
score without executed evidence, a real deployment, an independent CI run, and a
real external human review. The score is honest by construction — it cannot be
lifted to ≥95 while those preconditions are unmet.
"""

from .audit import run_audit
from .rubric import CATEGORIES, GOAL_TOTAL, TOTAL_POINTS
from .scoring import IterationRecord, ProductionScore, score

__all__ = ["run_audit", "score", "ProductionScore", "IterationRecord",
           "CATEGORIES", "TOTAL_POINTS", "GOAL_TOTAL"]
