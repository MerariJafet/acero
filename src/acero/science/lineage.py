"""Semantic exploration ledger + hypothesis lineage — catch SEMANTIC HARKing.

The reviewer: a search-space ledger of columns/models/seeds is necessary but insufficient,
because the scientific search happens BEFORE the code. An LLM can do *semantic* HARKing —
retrospectively reinterpreting what it found as if it were what it originally sought —
without changing a single statistical test.

So we record the semantic layer too: questions considered, hypotheses discarded, datasets
rejected, search terms, papers that shifted direction, endpoint/interpretation/title
changes, and — critically — WHETHER each decision was made after seeing results. A
result-sensitive change made after seeing results is HARKing risk: it increments
exploration debt and forbids confirmatory classification unless NEW independent evidence
arrives. The hypothesis lineage graph lets the dossier reconstruct how the final claim
evolved from the initial idea.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..core.clock import now_iso


class SemanticEventKind(str, Enum):
    QUESTION = "question_considered"
    HYPOTHESIS_DISCARDED = "hypothesis_discarded"
    DATASET_REJECTED = "dataset_rejected"
    SEARCH_TERM = "search_term"
    PAPER_INFLUENCE = "paper_influence"
    PROMPT_SHIFT = "prompt_shift"
    ENDPOINT_CHANGE = "endpoint_change"
    INTERPRETATION_CHANGE = "interpretation_change"
    HYPOTHESIS_REFRAME = "hypothesis_reframe"
    TITLE_CHANGE = "title_change"
    METRIC_SELECT = "metric_select"
    FIGURE_SELECT = "figure_select"


# changes that, if made AFTER seeing results, are HARKing (the finding becomes the hypothesis)
_RESULT_SENSITIVE = frozenset({
    SemanticEventKind.ENDPOINT_CHANGE, SemanticEventKind.INTERPRETATION_CHANGE,
    SemanticEventKind.HYPOTHESIS_REFRAME, SemanticEventKind.TITLE_CHANGE,
    SemanticEventKind.METRIC_SELECT,
})

# forks in the SEMANTIC search space (each expands the garden of forking paths)
_SEMANTIC_FORKS = frozenset({
    SemanticEventKind.QUESTION, SemanticEventKind.HYPOTHESIS_DISCARDED,
    SemanticEventKind.DATASET_REJECTED, SemanticEventKind.HYPOTHESIS_REFRAME,
    SemanticEventKind.ENDPOINT_CHANGE, SemanticEventKind.METRIC_SELECT,
})


@dataclass
class SemanticEvent:
    kind: SemanticEventKind
    detail: str
    at: str
    after_results: bool = False


@dataclass
class SemanticExplorationLedger:
    events: list[SemanticEvent] = field(default_factory=list)
    _results_seen: bool = False

    def mark_results_seen(self) -> None:
        self._results_seen = True

    def record(self, kind: SemanticEventKind, detail: str,
               after_results: bool | None = None) -> SemanticEvent:
        ar = self._results_seen if after_results is None else after_results
        ev = SemanticEvent(kind, detail.strip(), now_iso(), ar)
        self.events.append(ev)
        return ev

    # convenience
    def question(self, d: str) -> SemanticEvent: return self.record(SemanticEventKind.QUESTION, d)
    def discard_hypothesis(self, d: str) -> SemanticEvent: return self.record(SemanticEventKind.HYPOTHESIS_DISCARDED, d)
    def reject_dataset(self, d: str) -> SemanticEvent: return self.record(SemanticEventKind.DATASET_REJECTED, d)
    def reframe(self, d: str) -> SemanticEvent: return self.record(SemanticEventKind.HYPOTHESIS_REFRAME, d)
    def change_endpoint(self, d: str) -> SemanticEvent: return self.record(SemanticEventKind.ENDPOINT_CHANGE, d)

    def harking_flags(self) -> list[SemanticEvent]:
        """Result-sensitive changes made AFTER seeing results — the HARKing signal."""
        return [e for e in self.events
                if e.after_results and e.kind in _RESULT_SENSITIVE]

    def semantic_forks(self) -> int:
        return len({(e.kind, e.detail) for e in self.events if e.kind in _SEMANTIC_FORKS})

    def confirmatory_allowed(self, has_new_independent_evidence: bool = False
                             ) -> tuple[bool, str]:
        """HARKing after results forbids confirmatory status unless NEW independent
        evidence has been gathered since the reframe."""
        flags = self.harking_flags()
        if flags and not has_new_independent_evidence:
            return False, (f"{len(flags)} cambio(s) sensibles al resultado tras ver los "
                           f"datos (HARKing) sin evidencia independiente nueva")
        return True, "sin HARKing pendiente"

    def summary(self) -> dict[str, object]:
        return {
            "n_events": len(self.events),
            "semantic_forks": self.semantic_forks(),
            "harking_flags": len(self.harking_flags()),
            "confirmatory_allowed": self.confirmatory_allowed()[0],
        }


@dataclass
class LineageNode:
    id: str
    statement: str
    stage: str            # idea | refined | tested | final
    after_results: bool = False


class HypothesisLineageGraph:
    """Directed genealogy from initial idea to final claim."""

    def __init__(self) -> None:
        self._nodes: dict[str, LineageNode] = {}
        self._edges: list[tuple[str, str, str]] = []   # (from, to, reason)
        self._origin: str | None = None

    def add(self, node_id: str, statement: str, stage: str,
            after_results: bool = False) -> None:
        self._nodes[node_id] = LineageNode(node_id, statement, stage, after_results)
        if self._origin is None:
            self._origin = node_id

    def link(self, from_id: str, to_id: str, reason: str = "") -> None:
        self._edges.append((from_id, to_id, reason))

    def trace(self, final_id: str) -> list[LineageNode]:
        """Path of statements from origin to the final claim (best-effort, acyclic)."""
        parents = {t: f for f, t, _ in self._edges}
        chain: list[LineageNode] = []
        cur: str | None = final_id
        seen: set[str] = set()
        while cur and cur in self._nodes and cur not in seen:
            seen.add(cur)
            chain.append(self._nodes[cur])
            cur = parents.get(cur)
        return list(reversed(chain))

    def final_reframed_after_results(self, final_id: str) -> bool:
        """Did the final claim (or any step on its path) get reframed after results?"""
        return any(n.after_results for n in self.trace(final_id))
