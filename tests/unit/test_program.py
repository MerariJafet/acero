"""Sprint 16 tests: Research Program OS — programs, portfolio, budget, retrospectives."""

from __future__ import annotations

import pytest

from acero.program.budget import BudgetExceeded, BudgetGuard
from acero.program.engine import ProgramEngine
from acero.program.models import (
    BudgetUsage,
    ComputeBudget,
    ProgramStatus,
    QuestionRole,
    Retrospective,
)
from acero.program.portfolio import DIMENSIONS, Portfolio


def _engine(disc_store):
    return ProgramEngine(disc_store)


# --- program lifecycle ----------------------------------------------------

def test_create_and_persist_program(disc_store):
    pe = _engine(disc_store)
    p = pe.create("mission X", domains=["astronomy"], central_question="Q central?")
    assert pe.get(p.id) is not None
    assert p.central_questions[0].role == QuestionRole.CENTRAL


def test_questions_by_role(disc_store):
    pe = _engine(disc_store)
    p = pe.create("m")
    pe.add_question(p.id, "instrumental q", QuestionRole.INSTRUMENTAL)
    pe.add_question(p.id, "prereq q", QuestionRole.PREREQUISITE)
    view = pe.strategic_view(p.id)
    assert "instrumental" in view["questions_by_role"]
    assert "prerequisite" in view["questions_by_role"]


def test_status_transition_persists(disc_store):
    pe = _engine(disc_store)
    p = pe.create("m")
    pe.set_status(p.id, ProgramStatus.ACTIVE)
    assert pe.get(p.id).status == ProgramStatus.ACTIVE


def test_milestones_no_external_events(disc_store):
    pe = _engine(disc_store)
    p = pe.create("m")
    pe.add_milestone(p.id, "Preregister", kind="review", target_date="2026-08-01")
    ms = pe.get(p.id).milestones
    assert ms[0].kind == "review" and ms[0].done is False


# --- budget (hard limits) -------------------------------------------------

def test_budget_guard_enforces_hard_limit():
    guard = BudgetGuard(ComputeBudget(llm_tokens=1000), BudgetUsage())
    guard.charge("llm_tokens", 600)
    assert guard.remaining("llm_tokens") == 400
    with pytest.raises(BudgetExceeded):
        guard.charge("llm_tokens", 600)                # would exceed → refused
    assert guard.usage.llm_tokens == 600               # no partial charge


def test_charge_budget_through_engine(disc_store):
    pe = _engine(disc_store)
    p = pe.create("m")
    p.compute_budget = ComputeBudget(download_mb=500)
    pe._save(p, summary="budget")
    pe.charge_budget(p.id, "download_mb", 200)
    with pytest.raises(BudgetExceeded):
        pe.charge_budget(p.id, "download_mb", 400)
    assert pe.get(p.id).budget_usage.download_mb == 200


def test_unknown_budget_resource_rejected():
    guard = BudgetGuard(ComputeBudget(), BudgetUsage())
    with pytest.raises(ValueError):
        guard.charge("bitcoins", 1)


# --- portfolio (no single opaque score) -----------------------------------

def test_portfolio_shows_all_dimensions():
    pf = Portfolio()
    s = pf.add("p1", {"information_gain": 0.9})
    assert set(s.dimensions) == set(DIMENSIONS)         # every dimension present/visible


def test_portfolio_ranks_but_keeps_dimensions():
    pf = Portfolio()
    pf.add("good", {"information_gain": 0.9, "feasibility": 0.9, "risk": 0.1})
    pf.add("bad", {"information_gain": 0.2, "feasibility": 0.3, "risk": 0.8})
    ranked = pf.ranked()
    assert ranked[0].project_id == "good"
    assert ranked[0].dimensions and ranked[-1].dimensions   # dims never collapsed away
    assert "NOT a single" in pf.as_dict()["note"]


def test_risk_and_cost_reduce_priority():
    pf = Portfolio()
    low_risk = pf.add("low", {"information_gain": 0.6, "risk": 0.1, "compute_cost": 0.1})
    high_risk = pf.add("high", {"information_gain": 0.6, "risk": 0.9, "compute_cost": 0.9})
    assert low_risk.composite_view > high_risk.composite_view


# --- retrospectives -------------------------------------------------------

def test_retrospective_records_dead_hypotheses(disc_store):
    pe = _engine(disc_store)
    p = pe.create("m")
    pe.add_retrospective(p.id, Retrospective(
        cycle="c1", learned=["periodicity != mechanism"],
        dead_hypotheses=["stable single period"], beliefs_changed=["quasiperiodic more likely"]))
    got = pe.get(p.id)
    assert got.retrospectives[0].dead_hypotheses == ["stable single period"]


def test_missing_program_raises(disc_store):
    with pytest.raises(KeyError):
        _engine(disc_store).strategic_view("nope")
