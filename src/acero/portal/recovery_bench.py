"""P1 — Pipeline-level recovery benchmark.

The missing test: does ACERO recover the RIGHT verdict on questions whose answer is
known? We feed it established POSITIVES (it should reach a robust/positive outcome) and
spurious NULLS (it should stay inconclusive/refuted). Without this we cannot tell an
honest 'inconclusive' from an incapable one.

This module holds the control set + the pure scoring logic (offline-testable). Running a
control live (`run_control`) drives create→generate→approve→mission→score and is a long,
Codex-heavy job — kept out of the unit tests on purpose.
"""

from __future__ import annotations

from typing import Any

# expected ∈ {"positive", "null"}. Questions chosen to be answerable with the mature
# NEA/astro resolvers so the data step is not the bottleneck.
CONTROL_SET: list[dict[str, Any]] = [
    # --- established POSITIVES (ACERO should NOT stay flatly inconclusive) ---
    {"id": "pos_metal_giants", "expected": "positive", "domain": "astronomy",
     "question": ("¿La ocurrencia de planetas gigantes gaseosos aumenta con la "
                  "metalicidad [Fe/H] de la estrella anfitriona? (efecto Fischer-Valenti, "
                  "establecido). Datos: NASA Exoplanet Archive, una sola tabla."),
     "rationale": "correlación metalicidad↔gigantes bien establecida en la literatura"},
    {"id": "pos_period_insol", "expected": "positive", "domain": "astronomy",
     "question": ("¿Los planetas de periodo orbital más corto reciben mayor insolación? "
                  "(relación físicamente forzada). Datos: NEA pscomppars, una tabla."),
     "rationale": "insolación ∝ 1/a² y a crece con el periodo — casi tautológico"},
    {"id": "pos_mass_radius", "expected": "positive", "domain": "astronomy",
     "question": ("¿Existe una relación masa–radio para planetas pequeños (<4 R⊕) en el "
                  "NASA Exoplanet Archive? Datos: pscomppars, una tabla."),
     "rationale": "relación masa-radio empírica establecida"},
    # --- spurious NULLS (ACERO should stay inconclusive / refute) ---
    {"id": "null_ra_radius", "expected": "null", "domain": "astronomy",
     "question": ("¿El radio planetario correlaciona con la ascensión recta (RA) de la "
                  "estrella? Datos: NEA pscomppars, una tabla."),
     "rationale": "coordenada del cielo no tiene relación causal con el radio"},
    {"id": "null_discyear_radius", "expected": "null", "domain": "astronomy",
     "question": ("¿El radio planetario depende del año de descubrimiento como propiedad "
                  "física (no como sesgo)? Datos: NEA, una tabla."),
     "rationale": "el año de descubrimiento es un artefacto observacional, no físico"},
    {"id": "null_hostname_len", "expected": "null", "domain": "astronomy",
     "question": ("¿La longitud del nombre de la estrella anfitriona predice el periodo "
                  "orbital del planeta? Datos: NEA, una tabla."),
     "rationale": "correlación absurda de control negativo"},
]


def derive_outcome(experiments: list[dict[str, Any]]) -> str:
    """Aggregate a project's REAL-data experiments into one outcome label:
      positive_robust | inconclusive | refuted | no_evidence.
    Only real (non-synthetic) experiments count; a 'supports' degraded by the
    cross-check counts as inconclusive (the honesty rule already rewrote it)."""
    reals = [e for e in experiments if e.get("synthetic") is False]
    verdicts = [(e.get("result") or {}).get("verdict") for e in reals]
    verdicts = [v for v in verdicts if v]
    if not verdicts:
        return "no_evidence"
    n = len(verdicts)
    sup = verdicts.count("supports")
    ref = verdicts.count("refutes")
    if sup and sup >= max(2, n // 2) and ref == 0:
        return "positive_robust"
    if ref and ref >= max(2, n // 2) and sup == 0:
        return "refuted"
    return "inconclusive"


def grade(expected: str, outcome: str) -> dict[str, Any]:
    """Did ACERO recover the right kind of answer?

    positive control → correct iff outcome is positive_robust.
    null control     → correct iff outcome is inconclusive/refuted/no_evidence
                       (a null control must NEVER come back positive_robust).
    """
    if expected == "positive":
        correct = outcome == "positive_robust"
        fail_mode = "" if correct else "no recuperó el positivo (posible incapacidad)"
    else:  # null
        correct = outcome in ("inconclusive", "refuted", "no_evidence")
        fail_mode = "" if correct else "FALSO POSITIVO en un control nulo (grave)"
    return {"expected": expected, "outcome": outcome, "correct": correct,
            "fail_mode": fail_mode}


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold per-control grades into a domain summary (feeds the calibration memory)."""
    pos = [r for r in results if r.get("expected") == "positive"]
    nul = [r for r in results if r.get("expected") == "null"]
    fp = sum(1 for r in nul if r.get("outcome") == "positive_robust")  # false positives
    tot = len(results) or 1
    return {
        "positives_correct": sum(1 for r in pos if r.get("correct")),
        "positives_total": len(pos),
        "nulls_correct": sum(1 for r in nul if r.get("correct")),
        "nulls_total": len(nul),
        "false_positives": fp,
        "accuracy": round(sum(1 for r in results if r.get("correct")) / tot, 3),
    }


def learn(domain: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """After a benchmark: record the retro and auto-tune the domain within guardrails.
    This is the loop that lets the program remember and improve per field."""
    from .calibration import Calibration
    c = Calibration()
    summary = summarize(results)
    c.record_benchmark(domain, summary)
    decision = c.auto_tune(domain)
    return {"summary": summary, "decision": decision}


def score_project(project_id: str, expected: str,
                  session_factory: Any | None = None) -> dict[str, Any]:
    """Read a finished project and grade it against its expected control label."""
    from ..discovery.store import DiscoveryStore
    from ..ledger.db import default_session_factory
    from ..ledger.service import ResearchLedger
    sf = session_factory or default_session_factory()
    store = DiscoveryStore(sf, ResearchLedger(sf))
    exps = store.list_objects(project_id, kind="experiment")
    outcome = derive_outcome(exps)
    return {"project_id": project_id, "n_experiments": len(exps), **grade(expected, outcome)}
