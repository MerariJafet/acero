"""Integrate investigation results into the World Model.

This is where "ran an experiment" becomes "changed what we believe". A Hidden
Dynamics report (or any structured result) is mapped onto Phenomenon / Model /
Experiment / Evidence / NegativeResult nodes and typed relations, and beliefs are
updated (support up for the winner, down for the overfitter), with replication.
"""

from __future__ import annotations

from typing import Any

from .anomalies import register_anomaly
from .contradictions import detect_contradictions
from .edges import EdgeType
from .graph import WorldModel
from .nodes import NodeType

# Predicted extrapolation behaviour per family (stance for contradiction detection).
FAMILY_STANCE = {
    "exponential": "monotonic", "damped": "oscillatory", "logistic": "saturating",
    "cubic": "monotonic", "linear": "monotonic", "poly9": "diverging", "mean": "flat",
}


def integrate_hidden_dynamics(wm: WorldModel, report: dict[str, Any], *,
                              program_id: str | None = None,
                              actor: str = "discovery") -> dict[str, Any]:
    system = report["system"]
    hidden = report.get("hidden_family")
    winner = report["winner_family"]
    seeds = report.get("seeds", [1])

    phenom = wm.get_or_create(NodeType.PHENOMENON, f"{system} dynamics",
                              domain="astronomy", program_id=program_id,
                              data={"system": system})
    experiment = wm.create(NodeType.EXPERIMENT,
                           f"Extrapolation discrimination on {system}",
                           domain="astronomy", program_id=program_id,
                           data={"eig_bits": report.get("eig_bits"),
                                 "reproduced": report.get("reproduced")})
    wm.link(EdgeType.TESTS, experiment.id, phenom.id)

    # One Model belief per family, with a stance (for contradiction detection).
    # EVERY model's belief is updated from its fit quality — the graph learns across
    # all competitors, not just the winner (audit fix for sparse learning).
    fam_rmse = report.get("family_mean_test_rmse", {})
    baseline = fam_rmse.get("mean") or (max(fam_rmse.values()) if fam_rmse else 1.0)
    model_nodes: dict[str, str] = {}
    for family, rmse in fam_rmse.items():
        stance = FAMILY_STANCE.get(family, "monotonic")
        m = wm.get_or_create(NodeType.MODEL, f"{family} model of {system}",
                             domain="astronomy", program_id=program_id,
                             data={"subject": f"{system}-extrapolation", "stance": stance,
                                   "family": family})
        wm.link(EdgeType.EXPLAINS, m.id, phenom.id, confidence=0.4)
        wm.link(EdgeType.TESTS, experiment.id, m.id)
        model_nodes[family] = m.id
        # Evidence strength: how much better than the naive baseline this model fits.
        ev_strength = max(0.0, 1.0 - rmse / baseline) if baseline > 0 else 0.0
        reps = max(0, len(seeds) - 1) if family == winner else 0
        wm.update_belief(m.id, event="experiment", evidence=ev_strength, replication=reps,
                         source=experiment.id, actor=actor)

    # Winner gets an explicit supporting Evidence node.
    if winner in model_nodes:
        ev = wm.create(NodeType.EVIDENCE,
                       f"{winner} best explains {system} out of sample",
                       domain="astronomy", program_id=program_id,
                       data={"test_rmse": fam_rmse.get(winner)})
        wm.link(EdgeType.SUPPORTS, ev.id, model_nodes[winner], weight=1.0, confidence=0.8)

    # poly9 overfitter: counter-evidence + negative result; belief down AND its
    # 'explains' relation is WEAKENED (deactivated), not deleted (audit fix:
    # demonstrate relations weakening over time).
    if "poly9" in model_nodes:
        neg = wm.create(NodeType.NEGATIVE_RESULT, f"poly9 fails to extrapolate on {system}",
                        domain="astronomy", program_id=program_id,
                        data={"extrapolation_rmse": report.get("poly9_extrapolation_rmse")})
        wm.link(EdgeType.INVALIDATES, neg.id, model_nodes["poly9"], confidence=0.9)
        wm.update_belief(model_nodes["poly9"], event="experiment", counter=1.5, negative=1,
                         source=experiment.id, actor=actor)
        for e in wm.edges(source=model_nodes["poly9"], etype=EdgeType.EXPLAINS):
            wm.reweight_edge(e.id, weight=0.1, deactivate=True)

    # Model recovery mismatch is an anomaly (kept until explained).
    anomaly = None
    if hidden and winner != hidden and hidden in model_nodes:
        anomaly = register_anomaly(
            wm, label=f"Winner '{winner}' != hidden family '{hidden}' on {system}",
            expected=hidden, observed=winner, experiment_id=experiment.id,
            domain="astronomy",
            candidate_explanations=[f"noise favoured {winner}",
                                    "fitter for the hidden family is weak",
                                    "insufficient extrapolation range"], actor=actor)

    # Detect contradictions among the model stances.
    contradictions = detect_contradictions(wm, actor=actor)

    return {
        "phenomenon_id": phenom.id, "experiment_id": experiment.id,
        "model_nodes": model_nodes, "winner": winner,
        "anomaly_id": anomaly.id if anomaly else None,
        "contradictions_created": len(contradictions),
    }
