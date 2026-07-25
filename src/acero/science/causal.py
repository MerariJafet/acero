"""CAUSA — Causal Assumption and Uncertainty Scientific Auditor.

The reviewer: before running an analysis, a hypothesis must become an explicit causal
model, and the system must answer FIRST — does this dataset let me *identify* the causal
question, or only detect an association? If causality is not identifiable, the system
must forbid causal language in the dossier.

This module implements the machinery to answer that computably: a DAG, an explicit
estimand (exposure, outcome, adjustment set, declared confounders/mediators/colliders),
Pearl's back-door criterion via d-separation, and a verdict that gates causal claims.

It is deliberately conservative: when in doubt it returns "association only". A DAG is a
declared assumption, not a fact — so identifiability here means "identifiable UNDER these
assumptions", which is exactly how the claim compiler will phrase it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class CausalGraph:
    """A directed acyclic graph of declared causal relations (edge a→b = 'a causes b')."""

    def __init__(self) -> None:
        self._children: dict[str, set[str]] = {}
        self._parents: dict[str, set[str]] = {}
        self._nodes: set[str] = set()

    def add_node(self, n: str) -> None:
        self._nodes.add(n)
        self._children.setdefault(n, set())
        self._parents.setdefault(n, set())

    def add_edge(self, a: str, b: str) -> None:
        self.add_node(a)
        self.add_node(b)
        self._children[a].add(b)
        self._parents[b].add(a)

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)

    def parents(self, n: str) -> set[str]:
        return set(self._parents.get(n, set()))

    def children(self, n: str) -> set[str]:
        return set(self._children.get(n, set()))

    def neighbors(self, n: str) -> set[str]:
        return self.parents(n) | self.children(n)

    def descendants(self, n: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.children(n))
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                stack.extend(self.children(x))
        return seen

    def has_cycle(self) -> bool:
        color: dict[str, int] = {}

        def visit(u: str) -> bool:
            color[u] = 1
            for v in self._children.get(u, set()):
                c = color.get(v, 0)
                if c == 1 or (c == 0 and visit(v)):
                    return True
            color[u] = 2
            return False

        return any(color.get(n, 0) == 0 and visit(n) for n in self._nodes)

    # --- d-separation / back-door ------------------------------------------
    def _all_paths(self, start: str, end: str) -> list[list[str]]:
        """Every simple (acyclic) undirected path between start and end."""
        paths: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            if node == end:
                paths.append(list(path))
                return
            for nb in sorted(self.neighbors(node)):
                if nb not in path:
                    path.append(nb)
                    dfs(nb, path)
                    path.pop()

        dfs(start, [start])
        return paths

    def _is_into(self, a: str, b: str) -> bool:
        """True if the edge between a,b points INTO b (a→b)."""
        return b in self._children.get(a, set())

    def _path_blocked(self, path: list[str], z: set[str]) -> bool:
        """d-separation: is this undirected path blocked given conditioning set z?"""
        for i in range(1, len(path) - 1):
            prev, w, nxt = path[i - 1], path[i], path[i + 1]
            collider = self._is_into(prev, w) and self._is_into(nxt, w)
            if collider:
                # collider blocks unless w or a descendant of w is conditioned on
                if w not in z and not (self.descendants(w) & z):
                    return True
            else:
                # chain / fork: blocked iff the middle node is conditioned on
                if w in z:
                    return True
        return False

    def backdoor_paths(self, x: str, y: str) -> list[list[str]]:
        """Paths from x to y whose first edge points INTO x (confounding paths)."""
        return [p for p in self._all_paths(x, y)
                if len(p) >= 2 and self._is_into(p[1], x)]

    def satisfies_backdoor(self, x: str, y: str, z: set[str]) -> tuple[bool, str]:
        """Pearl's back-door criterion for adjustment set z relative to (x → y)."""
        desc_x = self.descendants(x)
        bad = z & desc_x
        if bad:
            return False, f"el conjunto de ajuste incluye descendientes de la exposición: {sorted(bad)}"
        open_paths = [p for p in self.backdoor_paths(x, y)
                      if not self._path_blocked(p, z)]
        if open_paths:
            return False, f"quedan {len(open_paths)} camino(s) traseros abiertos (confusión no controlada)"
        return True, "todos los caminos traseros están bloqueados por el conjunto de ajuste"

    def opened_colliders(self, x: str, y: str, z: set[str]) -> list[str]:
        """Colliders (or their descendants) in z that OPEN a spurious path x…y."""
        out: set[str] = set()
        for p in self._all_paths(x, y):
            for i in range(1, len(p) - 1):
                prev, w, nxt = p[i - 1], p[i], p[i + 1]
                if self._is_into(prev, w) and self._is_into(nxt, w):
                    if w in z or (self.descendants(w) & z):
                        out.add(w)
        return sorted(out)


@dataclass
class Estimand:
    """The explicit causal quantity — vague 'X associated with Y' is not enough."""
    exposure: str
    outcome: str
    unit: str
    population: str
    adjustment_set: tuple[str, ...] = ()
    confounders: tuple[str, ...] = ()
    mediators: tuple[str, ...] = ()
    colliders: tuple[str, ...] = ()

    def text(self) -> str:
        z = ", ".join(self.adjustment_set) or "∅"
        return (f"efecto de {self.exposure} sobre {self.outcome} en {self.unit} "
                f"de {self.population}, ajustando por {{{z}}}")


@dataclass
class CausalVerdict:
    identifiable: bool
    reason: str
    opened_colliders: list[str] = field(default_factory=list)
    conditioned_mediators: list[str] = field(default_factory=list)

    @property
    def allows_causal_language(self) -> bool:
        return self.identifiable and not self.opened_colliders \
            and not self.conditioned_mediators


def audit(estimand: Estimand, dag: CausalGraph) -> CausalVerdict:
    """Answer FIRST: is the causal question identifiable under this DAG? If not, no
    causal language is permitted downstream (only 'association')."""
    if dag.has_cycle():
        return CausalVerdict(False, "el DAG declarado tiene ciclos: no es un DAG válido")
    x, y = estimand.exposure, estimand.outcome
    if x not in dag.nodes or y not in dag.nodes:
        return CausalVerdict(False, "exposición u outcome no están en el DAG declarado")
    z = set(estimand.adjustment_set)
    conditioned_mediators = sorted(z & set(estimand.mediators)
                                   | (z & (dag.descendants(x) & dag.parents(y))))
    ok, reason = dag.satisfies_backdoor(x, y, z)
    opened = dag.opened_colliders(x, y, z)
    identifiable = ok and not opened and not conditioned_mediators
    if not identifiable and ok and (opened or conditioned_mediators):
        reason = "el back-door se cumple pero el ajuste abre un colisionador o controla un mediador"
    return CausalVerdict(identifiable, reason, opened, conditioned_mediators)
