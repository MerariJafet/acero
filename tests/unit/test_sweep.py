"""Mass parallel sweep — generate K, filter concurrently by novelty + EVA, rank."""
from __future__ import annotations

from acero.portal.sweep import SweepEngine


def _gen(pid, n, focus):
    # 4 candidates with distinct fates
    return [
        {"id": "h_good", "title": "predicción a priori con datos independientes"},
        {"id": "h_known", "title": "algo ya publicado"},
        {"id": "h_vague", "title": "algo vago"},
        {"id": "h_ok2", "title": "otra buena"},
    ]


def _novelty(hyp):
    if hyp["id"] == "h_known":
        return {"verdict": "already_resolved", "recovery_risk": 0.95}
    return {"verdict": "likely_open", "recovery_risk": 0.2}


def _eva(hyp):
    if hyp["id"] == "h_vague":
        return {"proceed": False, "blockers": ["demasiado vaga"]}
    return {"proceed": True, "blockers": []}


def _engine():
    return SweepEngine(generator=_gen, novelty=_novelty, eva=_eva)


def test_sweep_keeps_only_novel_and_eva_clean():
    out = _engine().run("p1", n=4)
    assert out["generated"] == 4 and out["evaluated"] == 4
    kept_ids = {s["title"] for s in out["survivors"]}
    assert "predicción a priori con datos independientes" in kept_ids
    assert out["kept"] == 2                          # 2 good, 1 known, 1 vague dropped


def test_already_resolved_is_rejected_with_reason():
    out = _engine().run("p1", n=4)
    reasons = {r["title"]: r["reason"] for r in out["rejected"]}
    assert "ya resuelto en literatura" in reasons.get("algo ya publicado", "")
    assert "vaga" in reasons.get("algo vago", "")


def test_survivors_are_ranked_by_score():
    out = _engine().run("p1", n=4)
    scores = [s["score"] for s in out["survivors"]]
    assert scores == sorted(scores, reverse=True) and all(s > 0 for s in scores)


def test_empty_generation_is_safe():
    out = SweepEngine(generator=lambda *a: [], novelty=_novelty, eva=_eva).run("p", n=4)
    assert out["generated"] == 0 and out["kept"] == 0


def test_one_bad_candidate_does_not_kill_the_sweep():
    def novelty(hyp):
        if hyp["id"] == "h_known":
            raise RuntimeError("boom")
        return {"verdict": "likely_open", "recovery_risk": 0.2}
    out = SweepEngine(generator=_gen, novelty=novelty, eva=_eva).run("p", n=4)
    assert out["evaluated"] == 3                      # the crashing one is skipped, others survive
