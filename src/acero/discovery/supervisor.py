"""Discovery supervisor: reusable orchestration of the hypothesis→experiment steps.

Ties generation, diversity, falsifiability, the tournament, experiment proposal, and
the critics together, persisting every object and decision (with provenance). It does
NOT execute experiments itself — execution is injected by the caller (the benchmark
or the CLI), so the same supervisor works with any sandbox/runner.
"""

from __future__ import annotations

from typing import Any

from ..ledger.service import ResearchLedger
from ..llm.factory import provider_from_config
from ..provenance.events import ProvenanceAction
from .candidates import CandidateStatus, HypothesisCandidate
from .experiment_critic import CodexExperimentCritic, RuleBasedExperimentCritic
from .experiment_design import ExperimentProposal, require_discriminating
from .falsifiability import is_falsifiable, score_candidate
from .generation import CodexHypothesisGenerator, MockHypothesisGenerator
from .store import DiscoveryStore
from .tournament import TournamentResult, run_tournament


class DiscoverySupervisor:
    def __init__(self, ledger: ResearchLedger, store: DiscoveryStore, project_id: str,
                 provider: Any | None = None) -> None:
        self.ledger = ledger
        self.store = store
        self.project_id = project_id
        self.provider = provider

    # --- Sprint 5: generation + tournament ------------------------------
    def generate(self, question: str, research_question_id: str, *,
                 context: dict[str, Any] | None = None, n: int = 8,
                 use_llm: bool = False) -> list[HypothesisCandidate]:
        gen: Any
        if use_llm and self.provider is not None and hasattr(self.provider, "complete_json"):
            gen = CodexHypothesisGenerator(self.provider)
        else:
            gen = MockHypothesisGenerator()
        candidates = gen.generate(question, project_id=self.project_id,
                                  research_question_id=research_question_id,
                                  context=context, n=n)
        for c in candidates:
            c.scores = score_candidate(c).as_dict()
            self.store.put(self.project_id, "candidate", c.id, c.model_dump(),
                           status=c.status.value, action=ProvenanceAction.GENERATE,
                           summary=f"generated hypothesis '{c.title}' via {gen.name}")
        self.ledger.record_event(
            self.project_id, ProvenanceAction.GENERATE, gen.name,
            f"Generated {len(candidates)} hypothesis candidates",
            {"n": len(candidates), "generator": gen.name})
        return candidates

    def filter_falsifiable(self, candidates: list[HypothesisCandidate]
                           ) -> list[HypothesisCandidate]:
        kept = []
        for c in candidates:
            if is_falsifiable(c):
                kept.append(c)
            else:
                self._reject(c, reason="not falsifiable (missing predictions/conditions)",
                             evaluator="rules")
        return kept

    def tournament(self, candidates: list[HypothesisCandidate], *, keep_top: int = 4,
                   weights: dict[str, float] | None = None,
                   llm_critique: dict[str, Any] | None = None) -> TournamentResult:
        result = run_tournament(candidates, weights=weights, llm_critique=llm_critique)
        by_id = {c.id: c for c in candidates}
        for rank, cid in enumerate(result.ranking):
            c = by_id[cid]
            if rank < keep_top:
                c.status = CandidateStatus.ACCEPTED
                c.scores = result.scores[cid].as_dict()["objectives"]
                self.store.update_payload(cid, c.model_dump(), status=c.status.value)
            else:
                self._reject(c, reason=f"tournament rank {rank + 1} (kept top {keep_top})",
                             evaluator="tournament",
                             scores=result.scores[cid].as_dict(),
                             reconsider_if="weights change or a discriminating experiment "
                                           "favours this mechanism")
        self.ledger.record_event(
            self.project_id, ProvenanceAction.RANK, "tournament",
            f"Ranked {len(candidates)} hypotheses; kept top {keep_top}",
            {"ranking": result.ranking, "weights": result.weights})
        return result

    def _reject(self, c: HypothesisCandidate, *, reason: str, evaluator: str,
                scores: dict | None = None, reconsider_if: str = "") -> None:
        c.status = CandidateStatus.REJECTED
        c.rejection = {"reason": reason, "evaluator": evaluator,
                       "scores": scores or {}, "reconsider_if": reconsider_if}
        # REJECTED candidates are kept, never deleted.
        self.store.put(self.project_id, "candidate", c.id, c.model_dump(),
                       status="REJECTED", action=ProvenanceAction.REJECT,
                       summary=f"rejected hypothesis '{c.title}': {reason}")

    def rejected(self) -> list[dict[str, Any]]:
        return self.store.list_objects(self.project_id, kind="candidate", status="REJECTED")

    # --- Sprint 6: experiment proposal + critics ------------------------
    def build_proposal(self, question: str, hypotheses: list[HypothesisCandidate],
                       predicted_outcomes: dict[str, str], *,
                       variables: list[str], parameter_space: dict[str, Any],
                       divergence_region: str = "") -> ExperimentProposal:
        proposal = ExperimentProposal(
            project_id=self.project_id, research_question=question,
            hypotheses_tested=[h.id for h in hypotheses],
            independent_variables=variables[:1], dependent_variables=variables[1:2],
            controlled_variables=["seed", "noise_level"],
            parameter_space=parameter_space,
            baseline="mean predictor", positive_control="known-family fit on clean data",
            negative_control="shuffled labels -> no better than baseline",
            metrics=["train_rmse", "val_rmse", "test_rmse", "extrapolation_rmse"],
            preregistered_predictions=predicted_outcomes,
            falsification_rules=["winner must beat baseline AND generalise out of range"],
            stopping_rules=["fixed seeds/noise; no adaptive search"],
            compute_budget={"cpu_seconds_per_run": 30},
            divergence_region=divergence_region or "extrapolation region beyond train_max",
            preregistered=True,
        )
        return proposal

    def critique_proposal(self, proposal: ExperimentProposal, *, use_llm: bool = False
                          ) -> dict[str, Any]:
        rule_report = RuleBasedExperimentCritic().review(proposal)
        matrix = require_discriminating(proposal)  # raises if non-discriminating
        out: dict[str, Any] = {"rules": rule_report.as_dict(),
                               "discriminating": matrix.is_discriminating}
        if use_llm and self.provider is not None:
            out["codex"] = CodexExperimentCritic(self.provider).review(proposal).as_dict()
        if not rule_report.ok:
            raise ValueError(f"Experiment blocked by rule critic: {rule_report.as_dict()}")
        return out


def make_supervisor(ledger: ResearchLedger, store: DiscoveryStore, project_id: str,
                    provider: Any | None = None) -> DiscoverySupervisor:
    return DiscoverySupervisor(ledger, store, project_id,
                               provider or provider_from_config())
