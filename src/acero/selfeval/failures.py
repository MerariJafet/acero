"""Failure memory (Sprint 18).

A durable, categorised record of failures (technical, methodological, statistical,
epistemological, pedagogical, security, ux, runtime, data) — each ideally with a regression
test. Seeded with the REAL failures fixed during v2 development so ACERO remembers them.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from .models import FailureRecord

FAILURE_SCOPE = "_failures"

# Real failures encountered + fixed during development, each with its regression test.
SEED_FAILURES: tuple[dict[str, Any], ...] = (
    {"source": "inference", "category": "statistical",
     "symptom": "surrogate significance used phase-randomization (preserves spectrum)",
     "root_cause": "invalid null for a spectral peak",
     "regression_test": "tests/science/test_stellar_variability.py::"
                        "test_ar1_surrogate_is_the_null_not_phase_randomization",
     "status": "FIXED", "severity": "high"},
    {"source": "studies", "category": "methodological",
     "symptom": "peak detector over-counted solar cycles (34 vs ~24)",
     "root_cause": "smoothing window too short; no minimum inter-peak separation",
     "regression_test": "tests/science/test_stellar_variability.py::"
                        "test_bootstrap_reports_cycle_count_and_ci",
     "status": "FIXED", "severity": "high"},
    {"source": "understanding", "category": "pedagogical",
     "symptom": "keyword echo scored a full pass",
     "root_cause": "grader lacked an echo guard",
     "regression_test": "tests/unit/test_understanding_gate_engine.py::"
                        "test_keyword_echo_does_not_score_full_pass",
     "status": "FIXED", "severity": "medium"},
    {"source": "epistemic_gate", "category": "security",
     "symptom": "a non-overridable rule id ('harking') did not match a real rule",
     "root_cause": "orphan id after gate generalization",
     "regression_test": "tests/unit/test_red_team_scorecard.py::"
                        "test_no_orphan_non_overridable_rules",
     "status": "FIXED", "severity": "medium"},
    {"source": "reliability", "category": "statistical",
     "symptom": "correlated human judgement counted as independent evidence",
     "root_cause": "dependency graph missed analyst/method sharing",
     "regression_test": "tests/unit/test_evidence_dependency.py::"
                        "test_shared_analyst_and_method_are_dependencies",
     "status": "FIXED", "severity": "medium"},
    {"source": "publication", "category": "epistemological",
     "symptom": "an approval could be reused for a modified dossier",
     "root_cause": "approval not bound to content hash",
     "regression_test": "tests/unit/test_publication_review.py::"
                        "test_export_blocked_if_dossier_changed_after_approval",
     "status": "FIXED", "severity": "high"},
)


class FailureMemory:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    def record(self, failure: FailureRecord) -> FailureRecord:
        self._store.put(FAILURE_SCOPE, "failure", failure.failure_id, failure.model_dump(),
                        status=failure.status, summary=f"failure[{failure.category}]")
        return failure

    def all(self) -> list[FailureRecord]:
        return [FailureRecord(**r)
                for r in self._store.list_objects(FAILURE_SCOPE, kind="failure")]

    def seed(self) -> int:
        existing = {f.symptom for f in self.all()}
        n = 0
        for f in SEED_FAILURES:
            if f["symptom"] not in existing:
                self.record(FailureRecord(**f))
                n += 1
        return n

    def by_category(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.all():
            out[f.category] = out.get(f.category, 0) + 1
        return out

    def without_regression_test(self) -> list[str]:
        return [f.failure_id for f in self.all()
                if f.status == "FIXED" and not f.regression_test]
