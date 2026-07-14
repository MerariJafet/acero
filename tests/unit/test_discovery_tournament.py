"""Sprint 5 tests: multiobjective tournament + rejected-candidate preservation."""

from __future__ import annotations

from acero.discovery.diversity import analyze
from acero.discovery.supervisor import DiscoverySupervisor
from acero.discovery.tournament import DEFAULT_WEIGHTS, run_tournament, score_objectives


def test_tournament_is_reproducible(mock_candidates):
    r1 = run_tournament(mock_candidates)
    r2 = run_tournament(mock_candidates)
    assert r1.ranking == r2.ranking
    assert r1.elo == r2.elo


def test_tournament_keeps_all_comparison_detail(mock_candidates):
    r = run_tournament(mock_candidates)
    n = len(mock_candidates)
    assert len(r.comparisons) == n * (n - 1) // 2  # full round robin retained
    for c in r.comparisons:
        assert c.winner in (c.a, c.b)


def test_objective_scores_are_transparent(mock_candidates):
    div = analyze(mock_candidates)
    scores = score_objectives(mock_candidates, div, DEFAULT_WEIGHTS)
    for s in scores.values():
        assert set(s.objectives) >= {"falsifiability", "diversity_contribution", "feasibility"}
        assert 0.0 <= s.weighted <= 1.5


def test_supervisor_persists_accepted_and_rejected(ledger, project, disc_store, mock_candidates):
    sup = DiscoverySupervisor(ledger, disc_store, project.id)
    for c in mock_candidates:
        disc_store.put(project.id, "candidate", c.id, c.model_dump(), status="PROPOSED")
    sup.tournament(mock_candidates, keep_top=4)
    accepted = disc_store.list_objects(project.id, kind="candidate", status="ACCEPTED")
    rejected = disc_store.list_objects(project.id, kind="candidate", status="REJECTED")
    assert len(accepted) == 4
    assert len(rejected) == len(mock_candidates) - 4
    # Rejected candidates keep their rejection rationale and cannot be deleted.
    for r in rejected:
        assert r["rejection"]["reason"]
        assert r["rejection"]["reconsider_if"]


def test_rejected_candidates_cannot_be_deleted(ledger, project, disc_store, mock_candidates):
    import pytest

    from acero.core.errors import IntegrityError

    sup = DiscoverySupervisor(ledger, disc_store, project.id)
    for c in mock_candidates:
        disc_store.put(project.id, "candidate", c.id, c.model_dump(), status="PROPOSED")
    sup.tournament(mock_candidates, keep_top=4)
    rejected = disc_store.list_objects(project.id, kind="candidate", status="REJECTED")
    with pytest.raises(IntegrityError):
        disc_store.delete(rejected[0]["id"])


def test_ranking_provenance_recorded(ledger, project, disc_store, mock_candidates):
    sup = DiscoverySupervisor(ledger, disc_store, project.id)
    for c in mock_candidates:
        disc_store.put(project.id, "candidate", c.id, c.model_dump(), status="PROPOSED")
    sup.tournament(mock_candidates, keep_top=4)
    actions = {p["action"] for p in ledger.provenance_for_project(project.id)}
    assert "RANK" in actions
    assert "REJECT" in actions
