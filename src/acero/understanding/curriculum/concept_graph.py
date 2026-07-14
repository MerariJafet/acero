"""Prerequisite / concept dependency graph.

Detects missing prerequisites, invalid cycles, minimum learning paths, foundational
concepts, unnecessary dependencies, and alternative routes. Relation types mirror the
Concept Engine / World Model vocabulary so the two can be integrated.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

# Edge relation kinds. Only ``requires`` and the *_depends_on relations are hard
# prerequisites; helps_understand / is_example_of / generalizes are soft links.
HARD_RELATIONS = {"requires", "mathematically_depends_on",
                  "conceptually_depends_on", "procedurally_depends_on"}
SOFT_RELATIONS = {"helps_understand", "is_example_of", "generalizes"}
ALL_RELATIONS = HARD_RELATIONS | SOFT_RELATIONS


@dataclass
class ConceptEdge:
    src: str            # concept that has the dependency
    dst: str            # concept it depends on
    relation: str


@dataclass
class ConceptGraph:
    """Directed graph where an edge src -> dst (relation) means src depends on dst."""

    edges: list[ConceptEdge] = field(default_factory=list)
    nodes: set[str] = field(default_factory=set)

    def add(self, src: str, dst: str, relation: str = "requires") -> None:
        if relation not in ALL_RELATIONS:
            raise ValueError(f"unknown relation {relation!r}")
        self.nodes.update((src, dst))
        self.edges.append(ConceptEdge(src, dst, relation))

    def _hard_deps(self, node: str) -> list[str]:
        return [e.dst for e in self.edges
                if e.src == node and e.relation in HARD_RELATIONS]

    def prerequisites_of(self, node: str, *, transitive: bool = True) -> list[str]:
        """All hard prerequisites of ``node`` (transitively by default)."""
        if not transitive:
            return sorted(set(self._hard_deps(node)))
        seen: set[str] = set()
        stack = list(self._hard_deps(node))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self._hard_deps(cur))
        return sorted(seen)

    def missing_prerequisites(self, node: str, known: set[str]) -> list[str]:
        return [p for p in self.prerequisites_of(node) if p not in known]

    def find_cycle(self) -> list[str] | None:
        """Return a hard-dependency cycle if one exists (invalid), else None."""
        color: dict[str, int] = {}          # 0=unvisited,1=in-stack,2=done
        parent: dict[str, str] = {}

        def dfs(u: str) -> list[str] | None:
            color[u] = 1
            for v in self._hard_deps(u):
                if color.get(v, 0) == 0:
                    parent[v] = u
                    r = dfs(v)
                    if r:
                        return r
                elif color.get(v) == 1:
                    cyc = [v, u]
                    w = u
                    while parent.get(w) and parent[w] != v:
                        w = parent[w]
                        cyc.append(w)
                    return list(reversed(cyc))
            color[u] = 2
            return None

        for n in self.nodes:
            if color.get(n, 0) == 0:
                r = dfs(n)
                if r:
                    return r
        return None

    def minimum_path(self, target: str, known: set[str]) -> list[str]:
        """A valid learning order (topological) covering only what's still missing."""
        if self.find_cycle():
            raise ValueError("cannot sequence: prerequisite cycle present")
        needed = set(self.missing_prerequisites(target, known)) | {target}
        needed -= known
        order: list[str] = []
        temp: set[str] = set()
        done: set[str] = set()

        def visit(n: str) -> None:
            if n in done or n not in needed:
                return
            temp.add(n)
            for d in self._hard_deps(n):
                if d in needed and d not in temp:
                    visit(d)
            temp.discard(n)
            done.add(n)
            order.append(n)

        visit(target)
        return order

    def foundational_concepts(self) -> list[str]:
        """Concepts with no hard prerequisites of their own (leaves)."""
        return sorted(n for n in self.nodes if not self._hard_deps(n))

    def alternative_routes(self, target: str) -> int:
        """Count distinct hard-prerequisite parents that reach ``target`` — a proxy for
        how many routes exist into it (>1 means the learner has options)."""
        parents = [e.src for e in self.edges
                   if e.dst == target and e.relation in HARD_RELATIONS]
        return len(set(parents))

    def unnecessary_dependencies(self) -> list[ConceptEdge]:
        """Hard edges that are redundant because a transitive path already implies them."""
        redundant: list[ConceptEdge] = []
        for e in self.edges:
            if e.relation not in HARD_RELATIONS:
                continue
            # is dst reachable from src WITHOUT this direct edge?
            if self._reachable(e.src, e.dst, exclude=e):
                redundant.append(e)
        return redundant

    def _reachable(self, src: str, dst: str, *, exclude: ConceptEdge) -> bool:
        q: deque[str] = deque(
            d for d in self._hard_deps(src)
            if not (src == exclude.src and d == exclude.dst))
        seen: set[str] = set()
        while q:
            cur = q.popleft()
            if cur == dst:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            q.extend(self._hard_deps(cur))
        return False
