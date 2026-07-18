"""The persistent, versioned epistemic graph — the World Model core.

Nodes are beliefs; edges are typed relations. Every mutation is versioned (node
history) and emits a provenance event. Beliefs are updated, never overwritten;
weakened relations are deactivated, not deleted.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.clock import now_iso
from ..core.errors import IntegrityError
from ..ledger.models import (
    WorldEdgeRow,
    WorldNodeHistoryRow,
    WorldNodeRow,
)
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction
from .belief import BeliefPolicy
from .edges import EdgeType, WorldEdge, make_edge
from .nodes import NodeType, WorldNode, make_node


class WorldModel:
    def __init__(self, session_factory: sessionmaker[Session], ledger: ResearchLedger,
                 project_id: str, policy: BeliefPolicy | None = None) -> None:
        self._sf = session_factory
        self.ledger = ledger
        self.project_id = project_id
        self.policy = policy or BeliefPolicy()

    # ------------------------------------------------------------------ nodes
    def add_node(self, node: WorldNode, *, actor: str = "system") -> WorldNode:
        with self._sf() as s:
            if s.get(WorldNodeRow, node.id):
                raise IntegrityError(f"World node {node.id} already exists")
            s.add(WorldNodeRow(
                id=node.id, project_id=self.project_id, program_id=node.program_id,
                type=node.type.value, label=node.label, domain=node.domain,
                version=node.version, confidence=node.confidence, payload=node.model_dump()))
            s.add(WorldNodeHistoryRow(node_id=node.id, version=node.version,
                                      at=now_iso(), payload=node.model_dump()))
            s.commit()
        self.ledger.record_event(self.project_id, ProvenanceAction.CREATE, actor,
                                 f"world node {node.type.value} '{node.label}'",
                                 {"node_type": node.type.value}, entity_id=node.id)
        return node

    def get_node(self, node_id: str) -> WorldNode | None:
        with self._sf() as s:
            row = s.get(WorldNodeRow, node_id)
            return WorldNode(**row.payload) if row else None

    def create(self, ntype: NodeType, label: str, **kw: Any) -> WorldNode:
        return self.add_node(make_node(self.project_id, ntype, label, **kw))

    def find_by_label(self, label: str, ntype: NodeType | None = None) -> WorldNode | None:
        for n in self.nodes(ntype):
            if n.label.strip().lower() == label.strip().lower():
                return n
        return None

    def get_or_create(self, ntype: NodeType, label: str, **kw: Any) -> WorldNode:
        existing = self.find_by_label(label, ntype)
        return existing if existing else self.create(ntype, label, **kw)

    def nodes(self, ntype: NodeType | None = None,
              program_id: str | None = None) -> list[WorldNode]:
        with self._sf() as s:
            stmt = select(WorldNodeRow).where(WorldNodeRow.project_id == self.project_id)
            if ntype is not None:
                stmt = stmt.where(WorldNodeRow.type == ntype.value)
            if program_id is not None:
                stmt = stmt.where(WorldNodeRow.program_id == program_id)
            return [WorldNode(**r.payload) for r in s.execute(stmt).scalars().all()]

    def page_nodes(self, *, offset: int = 0, limit: int = 50,
                   ntype: NodeType | None = None, search: str | None = None,
                   ) -> dict[str, Any]:
        """SQL-level paginated node listing — never loads the full graph.

        Uses ``LIMIT/OFFSET`` and a ``LIKE`` label filter at the database so a
        10,000-node project returns one page (and a total count) without
        materialising every node in Python. This is what the World Model Explorer
        calls; the whole-graph :meth:`nodes` is only for small internal jobs.
        """
        from sqlalchemy import func

        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        with self._sf() as s:
            base = select(WorldNodeRow).where(WorldNodeRow.project_id == self.project_id)
            count_q = select(func.count()).select_from(WorldNodeRow).where(
                WorldNodeRow.project_id == self.project_id)
            if ntype is not None:
                base = base.where(WorldNodeRow.type == ntype.value)
                count_q = count_q.where(WorldNodeRow.type == ntype.value)
            if search:
                like = f"%{search.lower()}%"
                base = base.where(func.lower(WorldNodeRow.label).like(like))
                count_q = count_q.where(func.lower(WorldNodeRow.label).like(like))
            total = int(s.execute(count_q).scalar_one())
            rows = s.execute(
                base.order_by(WorldNodeRow.confidence.desc(), WorldNodeRow.id)
                .offset(offset).limit(limit)).scalars().all()
            items = [{"id": r.id, "label": r.label, "type": r.type,
                      "confidence": r.confidence, "version": r.version}
                     for r in rows]
        return {"total": total, "offset": offset, "limit": limit,
                "returned": len(items), "items": items,
                "has_more": offset + len(items) < total}

    def _save_node(self, s: Session, node: WorldNode) -> None:
        row = s.get(WorldNodeRow, node.id)
        if row is None:
            raise IntegrityError(f"World node {node.id} not found")
        node.version += 1
        node.updated_at = now_iso()
        row.payload = node.model_dump()
        row.version = node.version
        row.confidence = node.confidence
        row.label = node.label
        s.add(WorldNodeHistoryRow(node_id=node.id, version=node.version,
                                  at=node.updated_at, payload=node.model_dump()))

    def update_belief(self, node_id: str, *, event: str, evidence: float = 0.0,
                      counter: float = 0.0, replication: int = 0, negative: int = 0,
                      contradiction: int = 0, open_question: int = 0,
                      source: str | None = None, actor: str = "system") -> WorldNode:
        """Apply an evidence update to a node's belief. Versioned + provenance.

        A protected mutation (Sprint 10): when inline enforcement is active it must run
        inside a gate context, else BypassDetected is raised."""
        from ..epistemic_gate.transaction import require_context
        require_context("world_model.update_belief")
        with self._sf() as s:
            row = s.get(WorldNodeRow, node_id)
            if row is None:
                raise IntegrityError(f"World node {node_id} not found")
            node = WorldNode(**row.payload)
            state = node.belief_state()
            entry = state.apply(event=event, evidence=evidence, counter=counter,
                                replication=replication, negative=negative,
                                contradiction=contradiction, open_question=open_question,
                                source=source, policy=self.policy)
            node.set_belief(state)
            node.tested = node.tested or event in {"experiment", "dataset_test"}
            self._save_node(s, node)
            s.commit()
        self.ledger.record_event(
            self.project_id, ProvenanceAction.CONFIDENCE_UPDATE, actor,
            f"belief '{node.label}' {entry['confidence_before']}→{entry['confidence_after']}",
            {"event": event, "delta": entry["delta"]}, entity_id=node_id)
        return node

    def update_node_data(self, node_id: str, changes: dict[str, Any], *,
                         summary: str = "", actor: str = "system") -> WorldNode:
        """Update a node's ``data`` (non-belief metadata), versioned + provenance.
        Protected (Sprint 11)."""
        from ..epistemic_gate.transaction import require_context
        require_context("world_model.update_node_data")
        with self._sf() as s:
            row = s.get(WorldNodeRow, node_id)
            if row is None:
                raise IntegrityError(f"World node {node_id} not found")
            node = WorldNode(**row.payload)
            node.data.update(changes)
            self._save_node(s, node)
            s.commit()
        self.ledger.record_event(self.project_id, ProvenanceAction.UPDATE, actor,
                                 summary or f"update node data {node_id}", {},
                                 entity_id=node_id)
        return node

    def node_history(self, node_id: str) -> list[dict[str, Any]]:
        with self._sf() as s:
            rows = s.execute(
                select(WorldNodeHistoryRow).where(WorldNodeHistoryRow.node_id == node_id)
                .order_by(WorldNodeHistoryRow.version)).scalars().all()
            return [dict(r.payload) for r in rows]

    # ------------------------------------------------------------------ edges
    def link(self, etype: EdgeType, source: str, target: str, *, weight: float = 1.0,
             confidence: float = 0.5, actor: str = "system", **kw: Any) -> WorldEdge:
        """Create a typed relation. Idempotent: a duplicate (source, target, type)
        is NOT created again — the existing active edge is returned (audit fix for
        redundant relations). Protected: guarded by the inline gate (Sprint 10)."""
        from ..epistemic_gate.transaction import require_context
        require_context("world_model.link")
        with self._sf() as s:
            if not s.get(WorldNodeRow, source) or not s.get(WorldNodeRow, target):
                raise IntegrityError("Edge endpoints must be existing world nodes")
            existing = s.execute(
                select(WorldEdgeRow).where(
                    WorldEdgeRow.project_id == self.project_id,
                    WorldEdgeRow.source == source, WorldEdgeRow.target == target,
                    WorldEdgeRow.type == etype.value, WorldEdgeRow.active.is_(True))
            ).scalars().first()
            if existing is not None:
                return WorldEdge(**existing.payload)
            edge = make_edge(self.project_id, etype, source, target,
                             weight=weight, confidence=confidence, **kw)
            s.add(WorldEdgeRow(id=edge.id, project_id=self.project_id, type=etype.value,
                               source=source, target=target, active=True,
                               payload=edge.model_dump()))
            s.commit()
        self.ledger.record_event(self.project_id, ProvenanceAction.LINK, actor,
                                 f"{etype.value}: {source} -> {target}",
                                 {"edge_type": etype.value}, entity_id=edge.id)
        return edge

    def edges(self, *, source: str | None = None, target: str | None = None,
              etype: EdgeType | None = None, active_only: bool = True) -> list[WorldEdge]:
        with self._sf() as s:
            stmt = select(WorldEdgeRow).where(WorldEdgeRow.project_id == self.project_id)
            if source is not None:
                stmt = stmt.where(WorldEdgeRow.source == source)
            if target is not None:
                stmt = stmt.where(WorldEdgeRow.target == target)
            if etype is not None:
                stmt = stmt.where(WorldEdgeRow.type == etype.value)
            if active_only:
                stmt = stmt.where(WorldEdgeRow.active.is_(True))
            return [WorldEdge(**r.payload) for r in s.execute(stmt).scalars().all()]

    def reweight_edge(self, edge_id: str, *, weight: float | None = None,
                      confidence: float | None = None, deactivate: bool = False,
                      actor: str = "system") -> WorldEdge:
        """Strengthen/weaken a relation. Weakening to inactive is NOT deletion. Protected
        (Sprint 11): guarded by the inline gate."""
        from ..epistemic_gate.transaction import require_context
        require_context("world_model.reweight_edge")
        with self._sf() as s:
            row = s.get(WorldEdgeRow, edge_id)
            if row is None:
                raise IntegrityError(f"World edge {edge_id} not found")
            edge = WorldEdge(**row.payload)
            if weight is not None:
                edge.weight = weight
            if confidence is not None:
                edge.confidence = confidence
            if deactivate:
                edge.active = False
            edge.updated_at = now_iso()
            row.payload = edge.model_dump()
            row.active = edge.active
            s.commit()
        self.ledger.record_event(self.project_id, ProvenanceAction.UPDATE, actor,
                                 f"reweight edge {edge_id} (active={edge.active})",
                                 {"weight": edge.weight}, entity_id=edge_id)
        return edge

    # ------------------------------------------------------------------ networkx
    def to_networkx(self):  # pragma: no cover - thin adapter
        import networkx as nx

        g = nx.MultiDiGraph()
        for n in self.nodes():
            g.add_node(n.id, type=n.type.value, label=n.label, confidence=n.confidence,
                       domain=n.domain)
        for e in self.edges():
            g.add_edge(e.source, e.target, key=e.id, type=e.type.value,
                       weight=e.weight, confidence=e.confidence)
        return g

    def stats(self) -> dict[str, Any]:
        nodes = self.nodes()
        edges = self.edges(active_only=False)
        by_type: dict[str, int] = {}
        for n in nodes:
            by_type[n.type.value] = by_type.get(n.type.value, 0) + 1
        edge_types: dict[str, int] = {}
        for e in edges:
            edge_types[e.type.value] = edge_types.get(e.type.value, 0) + 1
        return {
            "n_nodes": len(nodes), "n_edges": len(edges),
            "nodes_by_type": by_type, "edges_by_type": edge_types,
            "active_edges": sum(1 for e in edges if e.active),
        }
