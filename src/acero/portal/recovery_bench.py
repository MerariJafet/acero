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
    # --- CHEMISTRY (segundo dominio, para probar generalización del MOTOR) ---
    {"id": "chem_pos_mw_heavyatoms", "expected": "positive", "domain": "chemistry",
     "question": ("¿El peso molecular de los compuestos aumenta con su número de átomos "
                  "pesados (no-H)? Datos públicos de PubChem (propiedades de compuestos)."),
     "rationale": "relación casi tautológica: más átomos pesados → más masa"},
    {"id": "chem_pos_logp_carbons", "expected": "positive", "domain": "chemistry",
     "question": ("¿La lipofilicidad (XLogP) tiende a aumentar con el número de átomos de "
                  "carbono? Datos de PubChem."),
     "rationale": "tendencia establecida: más carbonos → más hidrofóbico"},
    {"id": "chem_null_mw_namealpha", "expected": "null", "domain": "chemistry",
     "question": ("¿El peso molecular correlaciona con el orden alfabético del nombre del "
                  "compuesto? Datos de PubChem."),
     "rationale": "el nombre no tiene relación física con la masa"},
    {"id": "chem_null_rings_cid", "expected": "null", "domain": "chemistry",
     "question": ("¿El número de anillos de un compuesto depende de su número de "
                  "identificación CID en PubChem? Datos de PubChem."),
     "rationale": "el CID es orden de registro, no una propiedad física"},
]


# --- STRESS batches (to make the calibration memory work hard). Each control carries
# its real data `domain` (so resolvers/anti-contamination work) AND a `batch` tag so we
# can run just that stress set. Answers are unambiguous by construction. ---
STRESS_CONTROLS: list[dict[str, Any]] = [
    # s1 — astronomy, SPECIFICITY stress: tempting/absurd NULLS + 1 positive anchor.
    {"id": "s1_null_radius_dec", "batch": "s1", "domain": "astronomy", "expected": "null",
     "question": "¿El radio planetario (pl_rade) correlaciona con la declinación (dec) de "
                 "la estrella? Datos NEA pscomppars, una tabla.",
     "rationale": "la coordenada del cielo no tiene relación física con el radio"},
    {"id": "s1_null_ecc_ra", "batch": "s1", "domain": "astronomy", "expected": "null",
     "question": "¿La excentricidad orbital (pl_orbeccen) correlaciona con la ascensión "
                 "recta (ra) de la estrella? Datos NEA pscomppars.",
     "rationale": "coordenada del cielo, sin vínculo físico"},
    {"id": "s1_null_period_cid", "batch": "s1", "domain": "astronomy", "expected": "null",
     "question": "¿El periodo orbital (pl_orbper) depende del orden de registro del "
                 "planeta en el catálogo (índice de fila)? Datos NEA pscomppars.",
     "rationale": "el orden de registro es un artefacto, no una propiedad física"},
    {"id": "s1_pos_mass_radius", "batch": "s1", "domain": "astronomy", "expected": "positive",
     "question": "¿Los planetas más masivos (pl_bmasse) tienden a tener mayor radio "
                 "(pl_rade)? Relación masa-radio en NEA pscomppars.",
     "rationale": "ancla positiva establecida"},
    # s2 — astronomy, SENSITIVITY stress: real effects (some subtle) + 1 null.
    {"id": "s2_pos_teq_insol", "batch": "s2", "domain": "astronomy", "expected": "positive",
     "question": "¿La temperatura de equilibrio (pl_eqt) aumenta con la insolación "
                 "(pl_insol)? Datos NEA pscomppars.",
     "rationale": "relación física directa"},
    {"id": "s2_pos_grav_mass", "batch": "s2", "domain": "astronomy", "expected": "positive",
     "question": "¿La gravedad superficial (∝ pl_bmasse/pl_rade^2) aumenta con la masa "
                 "planetaria a radio comparable? Calcular desde NEA pscomppars.",
     "rationale": "g = GM/R^2, efecto real computable"},
    {"id": "s2_pos_teq_steff", "batch": "s2", "domain": "astronomy", "expected": "positive",
     "question": "¿Los planetas alrededor de estrellas más calientes (st_teff) tienen "
                 "mayor temperatura de equilibrio (pl_eqt) en promedio? NEA pscomppars.",
     "rationale": "tendencia real (más luminosa, más caliente el planeta)"},
    {"id": "s2_null_radius_glon", "batch": "s2", "domain": "astronomy", "expected": "null",
     "question": "¿El radio planetario (pl_rade) correlaciona con la longitud galáctica "
                 "(glon) de la estrella? NEA pscomppars.",
     "rationale": "coordenada galáctica sin vínculo físico con el radio"},
    # s3 — chemistry, cross-domain reinforcement (PubChem).
    {"id": "s3_pos_tpsa_on", "batch": "s3", "domain": "chemistry", "expected": "positive",
     "question": "¿El área de superficie polar topológica (TPSA) aumenta con el número de "
                 "átomos de oxígeno + nitrógeno? Datos PubChem.",
     "rationale": "TPSA se define sobre O/N: casi tautológico"},
    {"id": "s3_pos_hbd_ohnh", "batch": "s3", "domain": "chemistry", "expected": "positive",
     "question": "¿El número de donadores de puente de hidrógeno aumenta con el número de "
                 "grupos OH y NH del compuesto? Datos PubChem.",
     "rationale": "relación establecida por definición de donador"},
    {"id": "s3_null_mw_cid", "batch": "s3", "domain": "chemistry", "expected": "null",
     "question": "¿El peso molecular correlaciona con el número CID de registro en "
                 "PubChem? Datos PubChem.",
     "rationale": "el CID es orden de registro, no una propiedad física"},
    {"id": "s3_null_xlogp_firstletter", "batch": "s3", "domain": "chemistry",
     "expected": "null",
     "question": "¿La lipofilicidad (XLogP) depende de la primera letra del nombre del "
                 "compuesto? Datos PubChem.",
     "rationale": "la inicial del nombre no tiene relación física"},
]
CONTROL_SET += STRESS_CONTROLS


def controls_for(domain: str) -> list[dict[str, Any]]:
    """The control questions for one domain (empty ⇒ that field isn't onboarded yet)."""
    return [c for c in CONTROL_SET if c.get("domain") == domain]


def controls_in_batch(batch: str) -> list[dict[str, Any]]:
    """The controls of a named stress batch (may span domains)."""
    return [c for c in CONTROL_SET if c.get("batch") == batch]


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


# A run is only VALID (safe to learn from) if enough controls actually produced
# evidence. If most come back `no_evidence`, the DATA PIPELINE failed (e.g. the LLM
# quota was exhausted and experiments never ran) — learning from that would teach the
# calibration a FALSE "low sensitivity" signal. This is the validity floor.
MIN_EVIDENCE_FRACTION = 0.5


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold per-control grades into a domain summary (feeds the calibration memory)."""
    pos = [r for r in results if r.get("expected") == "positive"]
    nul = [r for r in results if r.get("expected") == "null"]
    fp = sum(1 for r in nul if r.get("outcome") == "positive_robust")  # false positives
    no_ev = sum(1 for r in results if r.get("outcome") == "no_evidence")
    tot = len(results) or 1
    evidence_fraction = round((tot - no_ev) / tot, 3)
    return {
        "positives_correct": sum(1 for r in pos if r.get("correct")),
        "positives_total": len(pos),
        "nulls_correct": sum(1 for r in nul if r.get("correct")),
        "nulls_total": len(nul),
        "false_positives": fp,
        "no_evidence": no_ev,
        "evidence_fraction": evidence_fraction,
        # invalid ⇒ the pipeline didn't produce evidence (plumbing failure, not science)
        "valid": evidence_fraction >= MIN_EVIDENCE_FRACTION,
        "accuracy": round(sum(1 for r in results if r.get("correct")) / tot, 3),
    }


def learn(domain: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """After a benchmark: record the retro and (only if the run is VALID) auto-tune the
    domain within guardrails. This is the loop that lets the program improve per field
    — and refuse to 'learn' from a run where the data pipeline failed."""
    from .calibration import Calibration
    c = Calibration()
    summary = summarize(results)
    c.record_benchmark(domain, summary)
    if not summary["valid"]:
        return {"summary": summary,
                "decision": {"action": "skip_invalid",
                             "reason": (f"solo {summary['evidence_fraction']:.0%} de los "
                                        "controles produjo evidencia (pipeline caído): "
                                        "no se aprende de esta corrida")}}
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
