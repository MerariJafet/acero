"""Holdout manager — confirmatory data that stays genuinely inaccessible.

The reviewer: "Once the system saw the data, those data can no longer be an impartial
test." So confirmation needs evidence the system has NOT seen. This module carves a
dataset into a DISCOVERY part (free to explore) and a HOLDOUT part that is *locked*:
its membership is fixed and hashed up front, but its contents cannot be handed back
until an UnblindingEvent exists against a frozen protocol.

Splits are DETERMINISTIC (hash-based, not RNG) so they are reproducible and their
membership can be proven to have been fixed before unblinding. Group splits keep whole
entities (subject / center / scaffold) on one side — the single most common leakage the
reviewer warns about.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .preregistration import ProtocolRegistry


def _unit(key: str, salt: str) -> float:
    """Deterministic value in [0,1) from a key+salt (process-independent, unlike hash())."""
    h = hashlib.sha256(f"{salt}\x00{key}".encode()).hexdigest()
    return int(h[:16], 16) / float(1 << 64)


@dataclass(frozen=True)
class HoldoutSplit:
    strategy: str
    discovery_keys: frozenset[str]
    holdout_keys: frozenset[str]
    salt: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def split_hash(self) -> str:
        blob = (self.strategy + "|" + self.salt + "|"
                + ",".join(sorted(self.holdout_keys)))
        return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()

    def sizes(self) -> tuple[int, int]:
        return len(self.discovery_keys), len(self.holdout_keys)


def random_split(keys: list[str], holdout_frac: float = 0.3,
                 salt: str = "acero") -> HoldoutSplit:
    if not 0.0 < holdout_frac < 1.0:
        raise ValueError("holdout_frac debe estar en (0,1)")
    hold: set[str] = set()
    disc: set[str] = set()
    for k in keys:
        (hold if _unit(k, salt) < holdout_frac else disc).add(k)
    return HoldoutSplit("random", frozenset(disc), frozenset(hold), salt,
                        {"holdout_frac": holdout_frac})


def temporal_split(rows: dict[str, float], cutoff: float) -> HoldoutSplit:
    """rows: key -> time value. Holdout = strictly-later observations (a real test:
    the model is frozen on the past and evaluated on the future)."""
    disc = {k for k, t in rows.items() if t < cutoff}
    hold = {k for k, t in rows.items() if t >= cutoff}
    return HoldoutSplit("temporal", frozenset(disc), frozenset(hold), "",
                        {"cutoff": cutoff})


def group_split(row_groups: dict[str, str], holdout_frac: float = 0.3,
                salt: str = "acero") -> HoldoutSplit:
    """row_groups: key -> group id (subject/center/scaffold). WHOLE groups go to one
    side so no entity leaks across the split — the anti-leakage the reviewer demands."""
    if not 0.0 < holdout_frac < 1.0:
        raise ValueError("holdout_frac debe estar en (0,1)")
    groups = sorted(set(row_groups.values()))
    hold_groups = {g for g in groups if _unit(g, salt) < holdout_frac}
    disc = {k for k, g in row_groups.items() if g not in hold_groups}
    hold = {k for k, g in row_groups.items() if g in hold_groups}
    return HoldoutSplit("group", frozenset(disc), frozenset(hold), salt,
                        {"holdout_frac": holdout_frac, "n_groups": len(groups),
                         "grouping": True})


class HoldoutLockedError(PermissionError):
    """Raised when holdout contents are requested without a frozen, unblinded protocol."""


class HoldoutManager:
    """Owns a split and a protocol registry; the holdout stays locked until unblinded."""

    def __init__(self, split: HoldoutSplit, registry: ProtocolRegistry,
                 row_groups: dict[str, str] | None = None) -> None:
        self.split = split
        self.registry = registry
        self._row_groups = row_groups or {}
        self._revealed = False

    def discovery_keys(self) -> frozenset[str]:
        """Always available — exploration happens here."""
        return self.split.discovery_keys

    def reveal_holdout(self, protocol_hash: str,
                       by: str = "acero") -> frozenset[str]:
        """Hand back holdout membership ONLY against a frozen protocol; records the
        UnblindingEvent so the audit trail shows exactly when the seal was broken."""
        if not self.registry.can_unblind(protocol_hash):
            raise HoldoutLockedError(
                "el holdout está sellado: exige un protocolo confirmatorio congelado")
        self.registry.unblind(protocol_hash, self.split.split_hash, by)
        self._revealed = True
        return self.split.holdout_keys

    @property
    def is_revealed(self) -> bool:
        return self._revealed

    def leaks(self) -> list[str]:
        """Group ids present on BOTH sides (should be empty for a group split)."""
        if not self._row_groups:
            return []
        gd = {self._row_groups[k] for k in self.split.discovery_keys if k in self._row_groups}
        gh = {self._row_groups[k] for k in self.split.holdout_keys if k in self._row_groups}
        return sorted(gd & gh)
