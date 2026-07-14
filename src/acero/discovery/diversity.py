"""Hypothesis diversity: similarity, clustering, and diversity metrics (Sprint 5.3).

Deliberately does NOT depend on embeddings. It combines lexical (token-Jaccard)
similarity with STRUCTURAL rules (mechanism signature, numeric-parameter deltas)
so duplicates, paraphrases, mechanism-sharing, and param-only variants are all
detectable and explainable.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .candidates import HypothesisCandidate

_TOKEN = re.compile(r"[a-z0-9]+")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_STOP = {"the", "a", "an", "of", "to", "and", "in", "is", "are", "for", "on", "with",
         "model", "hypothesis", "la", "el", "de", "y", "en", "un", "una", "que"}

# Similarity thresholds (documented heuristics).
DUP_THRESHOLD = 0.82
PARAPHRASE_THRESHOLD = 0.6


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def statement_similarity(x: HypothesisCandidate, y: HypothesisCandidate) -> float:
    return jaccard(_tokens(x.statement + " " + x.mechanism),
                   _tokens(y.statement + " " + y.mechanism))


def _numbers(c: HypothesisCandidate) -> list[str]:
    return _NUM.findall(c.statement + " " + c.mechanism)


@dataclass
class PairRelation:
    a: str
    b: str
    similarity: float
    relation: str  # duplicate | paraphrase | shared_mechanism | param_only | distinct


def classify_pair(x: HypothesisCandidate, y: HypothesisCandidate) -> PairRelation:
    sim = statement_similarity(x, y)
    same_mech = x.mechanism_signature() == y.mechanism_signature() and x.mechanism_signature() != ""
    nums_differ = _numbers(x) != _numbers(y)
    if sim >= DUP_THRESHOLD:
        rel = "duplicate"
    elif same_mech and nums_differ:
        rel = "param_only"
    elif same_mech:
        rel = "shared_mechanism"
    elif sim >= PARAPHRASE_THRESHOLD:
        rel = "paraphrase"
    else:
        rel = "distinct"
    return PairRelation(a=x.id, b=y.id, similarity=round(sim, 4), relation=rel)


@dataclass
class DiversityReport:
    n: int
    duplicates: list[tuple[str, str]] = field(default_factory=list)
    paraphrases: list[tuple[str, str]] = field(default_factory=list)
    mechanism_clusters: list[list[str]] = field(default_factory=list)
    n_mechanisms: int = 0
    semantic_diversity: float = 0.0
    mechanism_diversity: float = 0.0
    prediction_diversity: float = 0.0
    assumption_coverage: int = 0
    effective_num_hypotheses: float = 0.0

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "n_duplicates": len(self.duplicates),
            "n_paraphrases": len(self.paraphrases),
            "n_mechanisms": self.n_mechanisms,
            "semantic_diversity": round(self.semantic_diversity, 4),
            "mechanism_diversity": round(self.mechanism_diversity, 4),
            "prediction_diversity": round(self.prediction_diversity, 4),
            "assumption_coverage": self.assumption_coverage,
            "effective_num_hypotheses": round(self.effective_num_hypotheses, 4),
            "mechanism_clusters": self.mechanism_clusters,
        }


def _cluster_by_mechanism(cands: list[HypothesisCandidate]) -> list[list[str]]:
    clusters: dict[str, list[str]] = {}
    for c in cands:
        clusters.setdefault(c.mechanism_signature(), []).append(c.id)
    return list(clusters.values())


def _effective_number(cluster_sizes: list[int]) -> float:
    """Inverse Simpson index: exp(Shannon entropy) over the cluster distribution."""
    total = sum(cluster_sizes)
    if total == 0:
        return 0.0
    probs = [s / total for s in cluster_sizes]
    entropy = -sum(p * math.log(p) for p in probs if p > 0)
    return math.exp(entropy)


def analyze(cands: list[HypothesisCandidate]) -> DiversityReport:
    n = len(cands)
    rep = DiversityReport(n=n)
    if n == 0:
        return rep

    sims: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            pr = classify_pair(cands[i], cands[j])
            sims.append(pr.similarity)
            if pr.relation == "duplicate":
                rep.duplicates.append((pr.a, pr.b))
            elif pr.relation == "paraphrase":
                rep.paraphrases.append((pr.a, pr.b))

    clusters = _cluster_by_mechanism(cands)
    rep.mechanism_clusters = clusters
    rep.n_mechanisms = len(clusters)
    rep.effective_num_hypotheses = _effective_number([len(c) for c in clusters])

    rep.semantic_diversity = (1.0 - sum(sims) / len(sims)) if sims else 1.0
    rep.mechanism_diversity = rep.n_mechanisms / n

    # Prediction diversity: average pairwise Jaccard distance over prediction sets.
    pred_sets = [{p.lower().strip() for p in c.predicted_observations} for c in cands]
    p_sims = []
    for i in range(n):
        for j in range(i + 1, n):
            p_sims.append(jaccard(pred_sets[i], pred_sets[j]))
    rep.prediction_diversity = (1.0 - sum(p_sims) / len(p_sims)) if p_sims else 1.0

    all_assumptions = {a.lower().strip() for c in cands for a in c.assumptions}
    rep.assumption_coverage = len(all_assumptions)
    return rep
