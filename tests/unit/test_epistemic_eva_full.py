"""F3: assumption auditor + boundary mapper + EVA two modes (offline)."""

from __future__ import annotations

from acero.epistemic.assumption_auditor import audit_assumptions, critical_assumptions
from acero.epistemic.claim_reconstructor import ClaimRecord, EvidenceType, ReplicationStatus
from acero.epistemic.eva import (
    EvaMode,
    InternalHypothesisFlags,
    audit_external,
    audit_internal,
)
from acero.epistemic.theory_boundary_mapper import BoundaryMap


def _claim(**over):
    base = dict(claim_id="c1", claim_text="X→Y", exposure_or_input="X",
                outcome_or_prediction="Y", effect_direction="pos",
                evidence_type=EvidenceType.OBSERVATIONAL, provenance_roots=("R",),
                replication_status=ReplicationStatus.INTERNAL_ONLY,
                assumptions=("no hay confusión", "la medida es fiable"))
    base.update(over)
    return ClaimRecord(**base)


def test_assumption_auditor_flags_critical():
    audits = audit_assumptions(_claim(), sensitivities={"no hay confusión": 0.9})
    crit = critical_assumptions(audits)
    assert any(a.assumption == "no hay confusión" for a in crit)
    assert audits[0].critical      # sorted critical-first


def test_boundary_mapper_detects_extrapolation():
    bm = BoundaryMap("c1")
    bm.add("peso_molecular", 200, 500)
    assert bm.extrapolations({"peso_molecular": 800})     # outside → flagged
    assert bm.is_within_domain({"peso_molecular": 350})
    assert bm.extrapolations({"logD": 3})                 # undeclared var → implicit extrap


def test_eva_external_mode_audits_knowledge():
    rep = audit_external(_claim())
    assert rep.mode is EvaMode.EXTERNAL_KNOWLEDGE_AUDIT
    assert rep.vulnerabilities and rep.n_actionable >= 1


def test_eva_internal_mode_blocks_bad_hypothesis():
    flags = InternalHypothesisFlags(is_reformulation_of_known=True,
                                    experiment_confirm_only=True)
    rep = audit_internal(_claim(), flags)
    assert rep.mode is EvaMode.INTERNAL_HYPOTHESIS_AUDIT
    assert not rep.recommend_proceed and len(rep.internal_blockers) == 2


def test_eva_internal_clean_hypothesis_proceeds():
    rep = audit_internal(_claim(), InternalHypothesisFlags())
    assert rep.recommend_proceed          # no fatal blockers, only vulnerabilities to probe


def test_eva_internal_simpler_explanation_added_as_vulnerability():
    rep = audit_internal(_claim(), InternalHypothesisFlags(simpler_explanation_exists=True))
    assert any("occam" in v.vulnerability_id for v in rep.vulnerabilities)
