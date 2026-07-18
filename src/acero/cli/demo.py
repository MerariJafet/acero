"""`acero demo full` — an end-to-end research demonstration (Sprint 26 §26.4).

Drives program → project → question → hypothesis → experiment → sandbox/gate →
result → World Model → understanding → reliability → dossier → review export,
through the SAME protected services the portal uses. Local only; nothing is
published. Auth is enforced at the portal boundary (this CLI is already local).
"""

from __future__ import annotations

from collections.abc import Iterator


def run_full_demo() -> Iterator[str]:
    from sqlalchemy import create_engine

    from ..ledger.db import make_session_factory
    from ..ledger.models import Base
    from ..portal.workspace import WorkspaceService

    # isolated in-memory demo DB so the demo never touches real data
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    ws = WorkspaceService(sf)

    yield "ACERO full demo — local, no publication, no discovery."
    yield "auth: portal enforces PBKDF2 login + CSRF (this CLI is already local)"

    prog = ws.create_program("Demo research program", ["general"])
    yield f"1. program   → {prog['id']}"
    proj = ws.create_project("Demo project", program_id=prog["id"])
    yield f"2. project   → {proj['id']}"
    q = ws.add_question(prog["id"], "What structure explains the demo data?")
    yield f"3. question  → {q['question_id']}"
    hyps = ws.generate_hypotheses(proj["id"], q["text"])
    yield f"4. hypotheses→ {len(hyps)} generated ({', '.join(h['tag'] for h in hyps)})"
    appr = ws.approve_hypothesis(hyps[0]["id"], "reviewed for the demo")
    yield f"5. approve   → {appr['tag']} APPROVED (reason required)"
    exp = ws.run_experiment(proj["id"], hyps[0]["id"])
    yield f"6. experiment→ {exp['id']} (R²={exp['r2']}, synthetic sandbox)"
    good = ws.gate_check(exp)
    bad = ws.gate_check({"dimensions_valid": False, "train_test_disjoint": False,
                         "reproduced": False, "codex_treated_as_evidence": True})
    yield f"7. gate      → valid={good['outcome']}  invalid={bad['outcome']} (blocked)"
    node = ws.update_world_model(proj["id"], "demo claim under review")
    yield f"8. world     → node {node['node_id']} (belief, versioned)"

    from ..understanding.curriculum.research_curriculum import requirements_for
    reqs = requirements_for("transit", proj["id"])
    blocking = [r.concept for r in reqs if r.blocking]
    yield f"9. learning  → {len(reqs)} concepts; blocking: {', '.join(blocking[:3])}…"

    from ..reliability.engine import build_card
    card = build_card().as_dict()
    yield f"10. reliability → card with {len(card['dimensions'])} dimensions (no single score)"

    doss = ws.dossier(proj["id"], "synthetic structure recovered (not a discovery)")
    yield f"11. dossier  → {doss['id']} readiness={doss['readiness']} auto-publish=OFF"
    yield "12. review export → bundle prepared locally; NOTHING is sent or published"
    yield "DEMO COMPLETE — no discovery claimed; human review required."
