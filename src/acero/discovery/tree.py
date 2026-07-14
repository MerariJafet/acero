"""Persistent research tree (Sprint 7.1/7.2).

Question -> Hypotheses -> Experiments. Each node records status, cost, priority,
dependency, result, information gain, decision, children, and the reason it was
expanded or pruned. Persisted through DiscoveryStore so it survives a restart.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id
from ..provenance.events import ProvenanceAction
from .store import DiscoveryStore


class NodeStatus(str, Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    PRUNED = "PRUNED"
    CANCELLED = "CANCELLED"
    RETRYABLE = "RETRYABLE"


class TreeNode(BaseModel):
    id: str = Field(default_factory=lambda: new_id("node"))
    project_id: str
    kind: str  # question | hypothesis | experiment
    title: str
    parent_id: str | None = None
    status: NodeStatus = NodeStatus.PROPOSED
    cost: float = 0.0
    priority: float = 0.5
    depends_on: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    information_gain: float | None = None
    decision: str = ""
    expansion_reason: str = ""
    prune_reason: str = ""
    ref_id: str | None = None   # candidate id / proposal id this node represents
    created_at: str = Field(default_factory=now_iso)


class ResearchTree:
    def __init__(self, store: DiscoveryStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id

    def add(self, node: TreeNode, *, expansion_reason: str = "") -> TreeNode:
        node.expansion_reason = expansion_reason or node.expansion_reason
        self.store.put(
            self.project_id, "tree_node", node.id, node.model_dump(),
            status=node.status.value, parent_id=node.parent_id,
            action=ProvenanceAction.CREATE,
            summary=f"tree {node.kind} '{node.title}' ({node.status.value})",
        )
        return node

    def get(self, node_id: str) -> TreeNode | None:
        p = self.store.get(node_id)
        return TreeNode(**p) if p else None

    def children(self, node_id: str) -> list[TreeNode]:
        return [TreeNode(**c) for c in self.store.children(node_id)]

    def all_nodes(self) -> list[TreeNode]:
        return [TreeNode(**p) for p in self.store.list_objects(self.project_id, kind="tree_node")]

    def set_status(self, node_id: str, status: NodeStatus, *, decision: str = "",
                   result: dict[str, Any] | None = None,
                   information_gain: float | None = None) -> TreeNode:
        node = self.get(node_id)
        if node is None:
            raise KeyError(f"tree node {node_id} not found")
        node.status = status
        if decision:
            node.decision = decision
        if result is not None:
            node.result = result
        if information_gain is not None:
            node.information_gain = information_gain
        action = ProvenanceAction.PRUNE if status == NodeStatus.PRUNED else ProvenanceAction.UPDATE
        self.store.update_payload(node_id, node.model_dump(), status=status.value)
        self.store.ledger.record_event(
            self.project_id, action, "system",
            f"tree node {node_id} -> {status.value}", {"decision": decision}, entity_id=node_id,
        )
        return node

    def prune(self, node_id: str, reason: str) -> TreeNode:
        node = self.get(node_id)
        if node is None:
            raise KeyError(f"tree node {node_id} not found")
        node.prune_reason = reason
        self.store.update_payload(node_id, node.model_dump())
        return self.set_status(node_id, NodeStatus.PRUNED, decision=f"pruned: {reason}")

    def frontier(self) -> list[TreeNode]:
        """Nodes eligible to run: experiments that are VALIDATED or QUEUED/RETRYABLE."""
        runnable = {NodeStatus.VALIDATED, NodeStatus.QUEUED, NodeStatus.RETRYABLE}
        return [n for n in self.all_nodes() if n.kind == "experiment" and n.status in runnable]
