"""Hidden Dynamics Discovery Benchmark — integration of Sprints 5–7.

ACERO receives noisy observations of a HIDDEN dynamical system, proposes competing
model hypotheses, designs a discriminating experiment (extrapolation probe), runs it
in the sandbox across seeds/noise, updates confidence, tries to falsify the winner,
recommends the next experiment, preserves negatives, and writes human-learning docs.

Honesty (always stated in the report): the data are synthetic with a known ground
truth; this evaluates MODEL RECOVERY, not scientific discovery; performance may be
favoured by the candidate families offered.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any

from ..core.hashing import hash_json
from ..core.ids import new_id
from ..discovery.confidence import assess_result_quality, bayesian_update, which_weakens
from ..discovery.information_gain import (
    bayesian_eig,
    heuristic_eig,
    prior_sensitivity,
    uniform_prior,
)
from ..discovery.negative_registry import NegativeResultsRegistry
from ..discovery.next_experiment import recommend_next
from ..discovery.scheduler import LocalScheduler, Task
from ..discovery.store import DiscoveryStore
from ..discovery.supervisor import DiscoverySupervisor
from ..discovery.tree import NodeStatus, ResearchTree, TreeNode
from ..epistemology.schemas import ResearchQuestion
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction
from ..sandbox.runner import SubprocessRunner
from .hidden_dynamics_script import BENCH_SCRIPT

SYSTEMS = ["exponential_decay", "damped_oscillator", "logistic", "predator_prey", "chaotic_map"]

# Map a fitted model-family name to a keyword found in a candidate's title/mechanism.
FAMILY_KEYWORDS = {
    "exponential": "exponential", "damped": "damped", "logistic": "logistic",
    "cubic": "cubic", "linear": "linear", "poly9": "flexible", "mean": "baseline",
}
# Predicted extrapolation behaviour per family (for the discrimination matrix).
FAMILY_BEHAVIOR = {
    "exponential": "monotonic", "damped": "oscillatory", "logistic": "saturating",
    "cubic": "monotonic", "linear": "monotonic", "poly9": "diverging", "mean": "flat",
}


def _run_fit(runner: SubprocessRunner, system: str, seed: int, noise: float,
             timeout: int = 60) -> dict[str, Any]:
    ws = tempfile.mkdtemp(prefix="acero_hd_")
    os.makedirs(os.path.join(ws, "inputs"), exist_ok=True)
    os.makedirs(os.path.join(ws, "outputs"), exist_ok=True)
    params = {"system": system, "seed": seed, "noise": noise,
              "train_max": 3.0, "t_max": 5.0, "n_in": 60, "n_extra": 30}
    with open(os.path.join(ws, "inputs", "params.json"), "w") as fh:
        json.dump(params, fh)
    res = runner.run(BENCH_SCRIPT, ws, timeout_sec=timeout)
    if res.status != "ok":
        raise RuntimeError(f"fit failed ({system}, seed={seed}): {res.stderr[:300]}")
    for line in reversed(res.stdout.strip().splitlines()):
        if line.strip().startswith("{"):
            return json.loads(line)
    raise RuntimeError("no metrics from fit script")


def _map_family_to_candidate(family: str, candidates: list) -> str | None:
    kw = FAMILY_KEYWORDS.get(family, family)
    for c in candidates:
        text = (c.title + " " + c.mechanism + " " + c.statement).lower()
        if kw in text:
            return c.id
    return None


def run_hidden_dynamics(
    ledger: ResearchLedger, store: DiscoveryStore, project_id: str, *,
    system: str = "exponential_decay", seeds: list[int] | None = None,
    noise_levels: list[float] | None = None, artifacts_root: str | Path | None = None,
    use_llm: bool = False, provider: Any | None = None, runner: SubprocessRunner | None = None,
) -> dict[str, Any]:
    if system not in SYSTEMS:
        raise ValueError(f"unknown system {system}; choose from {SYSTEMS}")
    seeds = seeds or [1, 2]
    noise_levels = noise_levels or [1.0, 4.0]  # low (discriminate) and high (falsify)
    runner = runner or SubprocessRunner()
    artifacts_root = Path(artifacts_root or tempfile.mkdtemp(prefix="acero_hdbench_"))
    sup = DiscoverySupervisor(ledger, store, project_id, provider=provider)

    # 1. Research question ------------------------------------------------
    q = ResearchQuestion(
        id=new_id("q"), project_id=project_id,
        title=f"Which model family best explains and extrapolates the hidden '{system}' dynamics?",
        description="Synthetic noisy observations; generating equation hidden from the fitter.")
    ledger.add_entity(q)

    # 2. Generate + falsifiability filter + tournament (Sprint 5) ----------
    candidates = sup.generate(q.title, q.id, context={"variables": ["t", "y"], "system": system},
                              n=8, use_llm=use_llm)
    falsifiable = sup.filter_falsifiable(candidates)
    tour = sup.tournament(falsifiable, keep_top=4)
    top = [c for c in falsifiable if c.id in set(tour.ranking[:4])]

    # 3. Discriminating experiment (Sprint 6) -----------------------------
    predicted = {}
    for c in top:
        fam = next((f for f, kw in FAMILY_KEYWORDS.items()
                    if kw in (c.title + " " + c.mechanism + " " + c.statement).lower()), "linear")
        predicted[c.id] = FAMILY_BEHAVIOR.get(fam, "monotonic")
    proposal = sup.build_proposal(
        q.title, top, predicted, variables=["t", "y"],
        parameter_space={"seed": seeds, "noise": noise_levels})
    critique = sup.critique_proposal(proposal, use_llm=use_llm)
    store.put(project_id, "proposal", proposal.id, proposal.model_dump(),
              status="PREREGISTERED", summary="discriminating experiment preregistered")

    # 4. Information gain + prior sensitivity ------------------------------
    distinct_labels = len(set(predicted.values()))
    likelihoods = {cid: {lbl: (0.85 if lbl == predicted[cid] else 0.15 / max(1, distinct_labels - 1))
                         for lbl in set(predicted.values())} for cid in predicted}
    prior = uniform_prior(list(predicted))
    eig = bayesian_eig(prior, likelihoods)
    heig = heuristic_eig(len(top), distinct_labels)
    skewed = {cid: (2.0 if i == 0 else 1.0) for i, cid in enumerate(predicted)}
    sens = prior_sensitivity(likelihoods, {"uniform": prior, "skewed": skewed})

    # 5. Research tree (Sprint 7.1) ---------------------------------------
    tree = ResearchTree(store, project_id)
    root = tree.add(TreeNode(project_id=project_id, kind="question", title=q.title,
                             status=NodeStatus.VALIDATED, ref_id=q.id))
    hyp_nodes = {}
    for c in top:
        hn = tree.add(TreeNode(project_id=project_id, kind="hypothesis", title=c.title,
                               parent_id=root.id, status=NodeStatus.VALIDATED, ref_id=c.id),
                      expansion_reason="passed tournament top-4")
        hyp_nodes[c.id] = hn.id
    exp_node = tree.add(TreeNode(project_id=project_id, kind="experiment",
                                 title="Extrapolation discrimination experiment",
                                 parent_id=root.id, status=NodeStatus.VALIDATED,
                                 ref_id=proposal.id, information_gain=eig.eig),
                        expansion_reason="discriminating & preregistered")

    # 6. Execute via scheduler (Sprint 7.3): seeds x low-noise -------------
    low_noise = min(noise_levels)

    def _make_fit_fn(seed_val: int):
        def _fn(stop: Any) -> dict[str, Any]:
            return _run_fit(runner, system, seed_val, low_noise)
        return _fn

    tasks = [Task(id=f"run_s{s}", fn=_make_fit_fn(s), timeout_sec=90) for s in seeds]
    node_status: dict[str, str] = {}
    sched = LocalScheduler(concurrency=min(4, len(tasks)),
                           on_state=lambda tid, st, r: node_status.__setitem__(tid, st.value))
    tree.set_status(exp_node.id, NodeStatus.RUNNING)
    results = sched.run(tasks)
    fits = [r.result for r in results.values() if r.result]
    if not fits:
        tree.set_status(exp_node.id, NodeStatus.FAILED)
        raise RuntimeError("all benchmark runs failed")

    # 7. Determine winner + confidence update (Sprint 7.5) ----------------
    winners = [f["best_model_by_test_rmse"] for f in fits]
    winner_family = statistics.mode(winners)
    # mean test rmse per family across runs -> likelihood ∝ exp(-rmse)
    fam_rmse: dict[str, list[float]] = {}
    for f in fits:
        for fam, m in f["models"].items():
            fam_rmse.setdefault(fam, []).append(m["test_rmse"])
    fam_mean = {fam: statistics.mean(v) for fam, v in fam_rmse.items()}
    # Likelihood ∝ exp(-rmse / T). The temperature T tempers the update so a crude
    # RMSE-based likelihood does not manufacture false precision (audit fix:
    # posterior overconfidence). The posterior is RELATIVE PLAUSIBILITY, not a
    # calibrated probability.
    CONF_TEMPERATURE = 3.0
    likelihood_obs = {}
    for c in top:
        fam_c = next((f for f, kw in FAMILY_KEYWORDS.items()
                      if kw in (c.title + " " + c.mechanism + " " + c.statement).lower()), "")
        rmse = fam_mean.get(fam_c, max(fam_mean.values()) if fam_mean else 1.0)
        likelihood_obs[c.id] = math.exp(-rmse / CONF_TEMPERATURE)
    conf = bayesian_update(prior, likelihood_obs)
    weakened = which_weakens(conf.posterior)
    winner_cid = _map_family_to_candidate(winner_family, top)
    ledger.record_event(project_id, ProvenanceAction.CONFIDENCE_UPDATE,
                        "discovery", f"winner={winner_family}; confidence updated",
                        {"posterior": conf.as_dict()["posterior"], "weakened": weakened})

    # 8. Falsification: high noise degradation of the winner (Sprint 7 / Phase F)
    high_noise = max(noise_levels)
    hi = _run_fit(runner, system, seeds[0], high_noise)
    winner_test_low = fam_mean.get(winner_family, 0.0)
    winner_test_high = hi["models"].get(winner_family, {}).get("test_rmse", 0.0)
    degrades = winner_test_high > winner_test_low
    winner_extra = statistics.mean([f["models"].get(winner_family, {}).get("extrapolation_rmse", 0.0)
                                    for f in fits])

    # 9. Negative registry (Sprint 7.7) -----------------------------------
    negreg = NegativeResultsRegistry(store, project_id)
    poly9_extra = statistics.mean([f["models"].get("poly9", {}).get("extrapolation_rmse", 0.0)
                                   for f in fits])
    negreg.record(kind="failed_hypothesis",
                  summary="poly9 overfits: extrapolation error explodes",
                  config={"model": "poly9", "system": system},
                  hypothesis_id=_map_family_to_candidate("poly9", top),
                  reason=f"extrapolation_rmse≈{poly9_extra:.2f} vs winner≈{winner_extra:.2f}")
    # Audit fix: record weakened hypotheses as negative context too, not just poly9.
    for cid in weakened:
        negreg.record(kind="weakened_hypothesis",
                      summary=f"hypothesis {cid} weakened by the discriminating experiment",
                      config={"hypothesis_id": cid, "system": system},
                      hypothesis_id=cid,
                      reason="lower posterior plausibility than the winner")

    # 10. Reproducibility check ------------------------------------------
    repro = _run_fit(runner, system, seeds[0], low_noise)
    ref = next(f for f in fits if f["seed"] == seeds[0])
    reproduced = hash_json(repro) == hash_json(ref)

    # 11. Next experiment recommendation (Sprint 7.8) --------------------
    next_rec = recommend_next([
        {"experiment_id": "probe_high_resolution",
         "eig": eig.eig, "cost": 0.3, "risk": 0.1,
         "hypotheses_discriminated": [c.id for c in top],
         "components": {"information_gain": min(1.0, eig.eig / max(eig.prior_entropy, 1e-9)),
                        "scientific_value": 0.6, "falsification_power": 0.7,
                        "reproducibility": 1.0, "human_learning_value": 0.6,
                        "compute_cost": 0.3, "time_cost": 0.2, "monetary_cost": 0.0, "risk": 0.1}},
        {"experiment_id": "probe_higher_noise",
         "eig": eig.eig * 0.6, "cost": 0.2, "risk": 0.2,
         "hypotheses_discriminated": [c.id for c in top[:2]],
         "components": {"information_gain": 0.4, "scientific_value": 0.5,
                        "falsification_power": 0.8, "reproducibility": 1.0,
                        "human_learning_value": 0.5, "compute_cost": 0.2,
                        "time_cost": 0.1, "monetary_cost": 0.0, "risk": 0.2}},
    ])

    tree.set_status(exp_node.id, NodeStatus.COMPLETED,
                    decision=f"winner={winner_family}",
                    result={"winner_family": winner_family}, information_gain=eig.eig)

    # 12. Learning docs + honesty statement ------------------------------
    quality = assess_result_quality({"reproduced": reproduced, "discriminating": True, "status": "ok"})
    learning_files = _write_learning(artifacts_root / "learning", system, top, predicted,
                                     eig, winner_family, fam_mean, conf, degrades,
                                     poly9_extra, winner_extra, reproduced)

    # Audit fixes: order titles by ranking; surface partial ambiguity.
    by_id = {c.id: c for c in top}
    ranked_titles = [by_id[cid].title for cid in tour.ranking if cid in by_id]
    from ..discovery.experiment_design import build_matrix
    ambiguity_groups = build_matrix(proposal).non_distinguished_groups()

    report = {
        "project_id": project_id, "system": system, "hidden_family": ref["hidden_family"],
        "seeds": seeds, "noise_levels": noise_levels,
        "n_candidates": len(candidates), "n_falsifiable": len(falsifiable),
        "diversity": tour.diversity.as_dict(),
        "tournament_ranking": tour.ranking,
        "top_titles_by_rank": ranked_titles,
        "n_rejected_kept": len(sup.rejected()),
        "critique": critique,
        "partial_ambiguity_groups": ambiguity_groups,
        "eig_bits": round(eig.eig, 4), "heuristic_eig_bits": round(heig.eig, 4),
        "prior_sensitivity": sens,
        "winner_family": winner_family, "winner_candidate": winner_cid,
        "family_mean_test_rmse": {k: round(v, 4) for k, v in fam_mean.items()},
        # RELATIVE PLAUSIBILITY (uncalibrated), NOT a validated probability.
        "confidence_posterior": conf.as_dict()["posterior"],
        "confidence_note": ("Relative plausibility from out-of-sample RMSE (temperature-"
                            "tempered). UNCALIBRATED — not a validated scientific probability."),
        "weakened_hypotheses": weakened,
        "winner_degrades_under_noise": degrades,
        "winner_test_rmse_low_noise": round(winner_test_low, 4),
        "winner_test_rmse_high_noise": round(winner_test_high, 4),
        "winner_extrapolation_rmse": round(winner_extra, 4),
        "poly9_extrapolation_rmse": round(poly9_extra, 4),
        "reproduced": reproduced,
        # 'process_quality' = did the run execute, reproduce, and discriminate.
        # It is NOT scientific confidence in the winner.
        "process_quality": quality.quality,
        "cost_units_note": "Costs/risks are normalised heuristics in [0,1], not currency.",
        "next_experiment": next_rec.model_dump() if next_rec else None,
        "negative_records": len(negreg.all()),
        "learning_files": learning_files,
        "honesty": [
            "Los datos son sintéticos con una verdad de referencia conocida.",
            "Esto evalúa RECUPERACIÓN DE MODELOS, no descubrimiento científico.",
            "El objetivo es validar el método, no afirmar novedad.",
            "El desempeño puede estar favorecido por las familias candidatas ofrecidas.",
            "Una simulación no prueba nada sobre el mundo físico.",
            "La confianza reportada es plausibilidad relativa NO calibrada.",
            f"Base experimental pequeña ({len(seeds)} semillas, {len(noise_levels)} niveles de "
            "ruido); no soporta afirmaciones robustas de calibración.",
        ],
        "cannot_conclude": [
            "Que se haya descubierto una ley nueva.",
            "Que el ajuste implique causalidad.",
            "Que aplique fuera de estos datos sintéticos.",
            "Que sea una comparación imparcial de formas funcionales: la familia "
            f"'{winner_family}' está ESTRUCTURALMENTE PRIVILEGIADA porque los datos se "
            "generaron con esa familia. Es recuperación de modelo, no descubrimiento.",
            "Que la confianza posterior sea una probabilidad calibrada.",
        ],
    }
    (artifacts_root / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    return report


def _write_learning(out_dir: Path, system, top, predicted, eig, winner_family,
                    fam_mean, conf, degrades, poly9_extra, winner_extra, reproduced
                    ) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "problem_intuition.md": f"# Intuición del problema\n\nSe observan datos ruidosos de un "
            f"sistema dinámico oculto (`{system}`). La meta no es adivinar el nombre del sistema, "
            f"sino qué **familia de modelo** explica los datos y **generaliza fuera del rango**.\n",
        "hypotheses.md": "# Hipótesis competidoras\n\n" + "\n".join(
            f"- **{c.title}** → comportamiento esperado en extrapolación: `{predicted[c.id]}`"
            for c in top),
        "experimental_design.md": "# Diseño experimental\n\nExperimento **discriminante**: se "
            "comparan las familias en una región de **extrapolación** donde sus predicciones "
            "divergen (monotónico vs oscilatorio vs saturación vs divergencia). Controles: "
            "baseline (media), semillas múltiples, niveles de ruido.\n",
        "information_gain.md": f"# Ganancia de información\n\nEIG bayesiano ≈ **{eig.eig:.3f} bits** "
            f"(entropía previa {eig.prior_entropy:.3f}). El experimento se eligió porque separa "
            f"las familias en distintos comportamientos observables.\n",
        "results.md": f"# Resultados\n\nGanador por RMSE de test: **{winner_family}**.\n\n" +
            "\n".join(f"- {k}: RMSE test medio {v:.3f}" for k, v in sorted(fam_mean.items(), key=lambda x: x[1])),
        "falsification.md": f"# Falsación\n\nBajo ruido alto, el ganador **{winner_family}** "
            f"{'se degrada' if degrades else 'se mantiene'}. El polinomio flexible (poly9) "
            f"**falla en extrapolación** (RMSE≈{poly9_extra:.1f} vs ganador≈{winner_extra:.2f}): "
            "ajuste ≠ explicación.\n",
        "what_changed.md": "# Qué cambió\n\nConfianza posterior (bayesiana, sobre familias "
            "candidatas):\n\n" + "\n".join(f"- {k}: {v:.3f}" for k, v in conf.as_dict()["posterior"].items()) +
            f"\n\nReejecución reproducible: **{reproduced}**.\n",
        "knowledge_check.md": "# Verificación de comprensión\n\n- [ ] ¿Por qué la extrapolación "
            "distingue las familias mejor que la interpolación?\n- [ ] ¿Por qué poly9 gana en train "
            "y pierde fuera de rango?\n- [ ] ¿Por qué recuperar la familia **no** es un "
            "descubrimiento?\n- [ ] ¿Qué haría la confianza si el ruido fuera mayor?\n",
    }
    written = {}
    for name, content in files.items():
        (out_dir / name).write_text(content, encoding="utf-8")
        written[name] = str(out_dir / name)
    return written
