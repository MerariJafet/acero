"""Experiment search over a parameter space (Sprint 7.4).

Implemented now: grid, random, and a simple adaptive (local) search, plus
tree expand/prune/backtrack helpers. Interfaces are left for Bayesian optimisation,
evolutionary search, and active learning (no heavy dependencies added yet).
"""

from __future__ import annotations

import itertools
import random
from typing import Any, Protocol


def grid_search(space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Full cartesian product of the discrete parameter grid."""
    if not space:
        return []
    keys = list(space)
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*(space[k] for k in keys))]


def random_search(space: dict[str, list[Any]], n: int, seed: int = 0) -> list[dict[str, Any]]:
    """Deterministic (seeded) random sampling of the grid without replacement when possible."""
    rng = random.Random(seed)
    grid = grid_search(space)
    if not grid:
        return []
    if n >= len(grid):
        return grid
    return rng.sample(grid, n)


def adaptive_search(
    evaluated: list[tuple[dict[str, Any], float]],
    space: dict[str, list[Any]],
    n: int = 3,
) -> list[dict[str, Any]]:
    """Local search around the best-so-far config.

    ``evaluated`` is [(config, score)] with higher score = better. Returns up to n
    neighbours of the best config (one parameter perturbed to an adjacent grid value).
    """
    if not evaluated:
        return random_search(space, n)
    best_cfg, _ = max(evaluated, key=lambda t: t[1])
    neighbours: list[dict[str, Any]] = []
    seen = {tuple(sorted(c.items())) for c, _ in evaluated}
    for key, values in space.items():
        if key not in best_cfg or best_cfg[key] not in values:
            continue
        idx = values.index(best_cfg[key])
        for delta in (-1, 1):
            j = idx + delta
            if 0 <= j < len(values):
                cand = dict(best_cfg)
                cand[key] = values[j]
                sig = tuple(sorted(cand.items()))
                if sig not in seen:
                    neighbours.append(cand)
                    seen.add(sig)
            if len(neighbours) >= n:
                return neighbours
    return neighbours[:n]


def prune_by_score(configs_scores: list[tuple[Any, float]], keep_top_k: int) -> tuple[list[Any], list[Any]]:
    """Keep the top-k configs; return (kept, pruned). Explainable, not random."""
    ordered = sorted(configs_scores, key=lambda t: t[1], reverse=True)
    kept = [c for c, _ in ordered[:keep_top_k]]
    pruned = [c for c, _ in ordered[keep_top_k:]]
    return kept, pruned


# --- interfaces for future strategies (no heavy deps yet) --------------------
class SearchStrategy(Protocol):
    def suggest(self, evaluated: list[tuple[dict[str, Any], float]],
               space: dict[str, list[Any]], n: int) -> list[dict[str, Any]]:
        ...


class BayesianOptimizer:
    """Placeholder for Bayesian optimisation (e.g. GP-EI). Interface only."""

    def suggest(self, evaluated, space, n):  # pragma: no cover - not implemented
        raise NotImplementedError("Bayesian optimisation is a documented future strategy.")


class EvolutionarySearch:
    """Placeholder for evolutionary/genetic search. Interface only."""

    def suggest(self, evaluated, space, n):  # pragma: no cover - not implemented
        raise NotImplementedError("Evolutionary search is a documented future strategy.")


class ActiveLearner:
    """Placeholder for active learning (query the most informative config). Interface only."""

    def suggest(self, evaluated, space, n):  # pragma: no cover - not implemented
        raise NotImplementedError("Active learning is a documented future strategy.")
