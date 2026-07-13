"""Retrieval evaluation: recall@k, precision@k, MRR over a labelled query set."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    recall_at_k: float
    precision_at_k: float
    mrr: float
    k: int
    n_queries: int


def evaluate(
    predictions: list[list[str]], relevants: list[set[str]], k: int
) -> RetrievalMetrics:
    """Compute retrieval metrics.

    predictions[i]: ranked fragment ids returned for query i.
    relevants[i]: set of ground-truth relevant fragment ids for query i.
    """
    if len(predictions) != len(relevants):
        raise ValueError("predictions and relevants must align")
    if not predictions:
        return RetrievalMetrics(0.0, 0.0, 0.0, k, 0)

    recalls, precisions, rr = [], [], []
    for preds, rel in zip(predictions, relevants, strict=True):
        topk = preds[:k]
        hit = len(set(topk) & rel)
        recalls.append(hit / len(rel) if rel else 0.0)
        precisions.append(hit / k if k else 0.0)
        first = next((i for i, p in enumerate(topk, start=1) if p in rel), None)
        rr.append(1.0 / first if first else 0.0)

    n = len(predictions)
    return RetrievalMetrics(
        recall_at_k=round(sum(recalls) / n, 4),
        precision_at_k=round(sum(precisions) / n, 4),
        mrr=round(sum(rr) / n, 4),
        k=k,
        n_queries=n,
    )
