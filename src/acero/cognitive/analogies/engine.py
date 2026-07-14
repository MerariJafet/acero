"""Analogy Engine (Sprint 8.6): build, validate, and persist scientific analogies.

Rejected/misleading analogies are preserved (evidence of what does NOT work). The
analogy is integrated into the World Model as SYSTEM nodes + a RELATION node +
ANALOGOUS_TO / MAPS_TO edges.
"""

from __future__ import annotations

from typing import Any

from ...sandbox.runner import SubprocessRunner
from ...world_model.edges import EdgeType
from ...world_model.graph import WorldModel
from ...world_model.nodes import NodeType
from . import validation as V
from .models import AnalogyStatus, AnalogyType, ScientificAnalogy, SystemRepresentation
from .structure import compare, score

_DEEP_STATUSES = {AnalogyStatus.STRUCTURALLY_SUPPORTED, AnalogyStatus.VALID_IN_REGIME,
                  AnalogyStatus.PARTIALLY_VALID}


class AnalogyEngine:
    def __init__(self, wm: WorldModel, runner: SubprocessRunner | None = None) -> None:
        self.wm = wm
        self.runner = runner or SubprocessRunner()

    def build(self, source: SystemRepresentation, target: SystemRepresentation, *,
              run_transfer: bool = True, generator: str = "rules") -> ScientificAnalogy:
        comp = compare(source, target)
        scores = score(comp)
        validations = [
            V.structural_test(comp),
            V.dimensional_test(source, target),
            V.mathematical_test(comp),
            V.limits_test(source, target),
            V.counterexample_test(comp),
        ]
        if run_transfer and comp["forms_match"] and "resonance" in comp["shared_dimensionless_groups"]:
            validations.append(V.predictive_transfer_test(source, target, runner=self.runner))
        status = V.determine_status(scores, validations, comp)

        analogy = ScientificAnalogy(
            project_id=self.wm.project_id,
            source_system=source.name, target_system=target.name,
            source_domain=source.domain, target_domain=target.domain,
            analogy_type=AnalogyType.STRUCTURAL if comp["forms_match"] else AnalogyType.SURFACE,
            entity_mapping=comp["role_mapping"],
            equation_mapping={"structural_form": source.structural_form}
            if comp["forms_match"] else {},
            invariant_mapping={i: i for i in comp["shared_invariants"]},
            preserved_structure=(["governing equation form"] if comp["forms_match"] else [])
            + [f"role:{r}" for r in comp["shared_roles"]],
            broken_structure=[f"missing_role:{r}" for r in comp["missing_roles"]]
            + ([] if comp["forms_match"] else ["different governing equation"]),
            transfer_predictions=self._transfer_predictions(comp),
            failure_conditions=self._failure_conditions(comp, status),
            scores=scores, validations=validations, status=status, generator=generator)
        self._persist(analogy, comp)
        return analogy

    def _transfer_predictions(self, comp: dict[str, Any]) -> list[str]:
        groups = set(comp["shared_dimensionless_groups"])
        out = []
        if "resonance" in groups:
            out.append("resonance ω₀ = sqrt(restoring/inertia) transfers across domains")
        if "fourier_number" in groups:
            out.append("self-similar spreading: characteristic width ∝ sqrt(D·t) "
                       "(Fourier number invariant)")
        return out

    def _failure_conditions(self, comp: dict[str, Any], status: AnalogyStatus) -> list[str]:
        out = []
        if status in (AnalogyStatus.MISLEADING, AnalogyStatus.BROKEN, AnalogyStatus.REJECTED):
            out.append("deep structure does not correspond; surface similarity is misleading")
        if comp["missing_roles"]:
            out.append(f"roles without correspondence: {comp['missing_roles']}")
        # Even a valid analogy has regime limits — state them (audit fix).
        if status in (AnalogyStatus.STRUCTURALLY_SUPPORTED, AnalogyStatus.VALID_IN_REGIME,
                      AnalogyStatus.PARTIALLY_VALID):
            out.append("breaks in the nonlinear / large-amplitude regime")
            out.append("with sources/sinks the conserved quantities differ")
            out.append("boundary conditions must be matched for the correspondence to hold")
        return out

    def _persist(self, analogy: ScientificAnalogy, comp: dict[str, Any]) -> None:
        src = self.wm.get_or_create(NodeType.SYSTEM, analogy.source_system,
                                    domain=analogy.source_domain)
        tgt = self.wm.get_or_create(NodeType.SYSTEM, analogy.target_system,
                                    domain=analogy.target_domain)
        rel = self.wm.create(NodeType.ANALOGY, f"analogy: {analogy.source_system} ~ "
                             f"{analogy.target_system}",
                             data={"analogy": analogy.model_dump(), "status": analogy.status.value,
                                   "deep_score": analogy.scores.deep_score()})
        self.wm.link(EdgeType.RELATED_TO, rel.id, src.id)
        self.wm.link(EdgeType.RELATED_TO, rel.id, tgt.id)
        # Only deep, non-misleading analogies get an ANALOGOUS_TO edge.
        if analogy.status in _DEEP_STATUSES:
            self.wm.link(EdgeType.ANALOGOUS_TO, src.id, tgt.id,
                         weight=analogy.scores.deep_score(), confidence=0.7)
            for s_var, t_var in comp["role_mapping"].items():
                self.wm.link(EdgeType.MAPS_TO, src.id, tgt.id,
                             data={"maps": f"{s_var}->{t_var}"})

    def analogies(self) -> list[ScientificAnalogy]:
        return [ScientificAnalogy(**n.data["analogy"])
                for n in self.wm.nodes(NodeType.ANALOGY) if "analogy" in n.data]

    def rejected(self) -> list[ScientificAnalogy]:
        return [a for a in self.analogies()
                if a.status in (AnalogyStatus.REJECTED, AnalogyStatus.MISLEADING,
                                AnalogyStatus.BROKEN)]
