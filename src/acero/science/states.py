"""Scientific state ladder — and ACERO's hard ceiling.

The reviewer's recommended architecture of states. ACERO may automate up to
CANDIDATO_A_PREPRINT; only external agents (peer reviewers, other labs) may move a result
past that. This is encoded so the ceiling is enforced, not merely intended.

Each rung requires the previous rung PLUS a specific piece of evidence. `max_reachable`
walks the ladder and stops at the first unmet condition — an honest report of exactly how
far a result has actually earned its way, not how far we'd like it to be.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ScientificState(IntEnum):
    IDEA = 0
    HIPOTESIS_EXPLORATORIA = 1
    EVIDENCIA_PRELIMINAR = 2
    RESULTADO_EXPLORATORIO_ROBUSTO = 3
    PROTOCOLO_CONFIRMATORIO_CONGELADO = 4
    CONFIRMADO_EN_HOLDOUT = 5
    REPLICADO_EN_DATASET_INDEPENDIENTE = 6
    REPRODUCIDO_POR_IMPLEMENTACION_INDEPENDIENTE = 7
    REVISADO_POR_EXPERTO_DEL_DOMINIO = 8
    CANDIDATO_A_PREPRINT = 9            # <-- ACERO CEILING
    EN_REVISION_POR_PARES = 10
    PUBLICADO = 11
    REPLICADO_EXTERNAMENTE = 12


ACERO_CEILING = ScientificState.CANDIDATO_A_PREPRINT


@dataclass
class StateEvidence:
    """Boolean facts that gate each rung (each earned by real machinery, not assertion)."""
    hypothesis_formulated: bool = False
    executed_with_null_test: bool = False
    robust: bool = False                       # survives sensitivity / nulls / subsets
    protocol_frozen: bool = False
    holdout_confirmed: bool = False
    independent_dataset: bool = False
    independent_implementation: bool = False
    expert_reviewed: bool = False
    preprint_ready: bool = False
    # external-only (ACERO never sets these itself)
    in_peer_review: bool = False
    published: bool = False
    externally_replicated: bool = False


# state -> the evidence flag required to REACH it from the previous state
_GUARD: dict[ScientificState, str] = {
    ScientificState.HIPOTESIS_EXPLORATORIA: "hypothesis_formulated",
    ScientificState.EVIDENCIA_PRELIMINAR: "executed_with_null_test",
    ScientificState.RESULTADO_EXPLORATORIO_ROBUSTO: "robust",
    ScientificState.PROTOCOLO_CONFIRMATORIO_CONGELADO: "protocol_frozen",
    ScientificState.CONFIRMADO_EN_HOLDOUT: "holdout_confirmed",
    ScientificState.REPLICADO_EN_DATASET_INDEPENDIENTE: "independent_dataset",
    ScientificState.REPRODUCIDO_POR_IMPLEMENTACION_INDEPENDIENTE: "independent_implementation",
    ScientificState.REVISADO_POR_EXPERTO_DEL_DOMINIO: "expert_reviewed",
    ScientificState.CANDIDATO_A_PREPRINT: "preprint_ready",
    ScientificState.EN_REVISION_POR_PARES: "in_peer_review",
    ScientificState.PUBLICADO: "published",
    ScientificState.REPLICADO_EXTERNAMENTE: "externally_replicated",
}


def max_reachable(evidence: StateEvidence) -> ScientificState:
    """Walk the ladder; stop at the first rung whose evidence flag is False."""
    state = ScientificState.IDEA
    for rung in list(ScientificState)[1:]:
        flag = _GUARD[rung]
        if getattr(evidence, flag):
            state = rung
        else:
            break
    return state


def acero_max_state(evidence: StateEvidence) -> ScientificState:
    """ACERO can never claim past its ceiling, whatever the evidence flags say."""
    return min(max_reachable(evidence), ACERO_CEILING)


def is_external_state(state: ScientificState) -> bool:
    return state > ACERO_CEILING


def next_required(evidence: StateEvidence) -> str:
    """The single next piece of evidence needed to advance one rung (for the dossier)."""
    current = max_reachable(evidence)
    if current >= ScientificState.REPLICADO_EXTERNAMENTE:
        return "nada: tope de la escalera"
    nxt = ScientificState(current + 1)
    if is_external_state(nxt):
        return f"{_GUARD[nxt]} (solo agentes externos)"
    return _GUARD[nxt]
