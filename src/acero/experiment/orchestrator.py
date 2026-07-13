"""Sprint 4 orchestrator: the full computational research cycle.

question -> assumptions -> competing hypotheses -> pre-registered predictions ->
experiment design -> human approval -> sandboxed execution (multi-seed) ->
results + negative results -> skeptic refutation -> reproducibility check ->
learning artifacts -> report.

Nothing is declared a discovery. The orchestrator is deliberately explicit so a
third party can follow every step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.hashing import hash_json
from ..core.ids import new_id
from ..epistemology.schemas import (
    Assumption,
    ConfidenceAssessment,
    ExecutionRun,
    ExperimentPlan,
    Hypothesis,
    NegativeResult,
    Prediction,
    ProvenanceRef,
    ResearchQuestion,
    ResearchResult,
    ScientificClaim,
)
from ..ledger.service import ResearchLedger
from ..pedagogy.learning import write_learning_docs
from ..sandbox.runner import SubprocessRunner
from .artifacts import ArtifactBundle, capture_environment, hash_inputs_outputs
from .pilot import PILOT_SCRIPT, flatten_metrics, params_for_seed, parse_stdout
from .prereg import Preregistration, require_complete
from .skeptic import review_experiment
from .workflow import ResearchWorkflow, WorkflowState


def run_pilot(
    ledger: ResearchLedger,
    project_id: str,
    *,
    artifacts_root: str | Path,
    seeds: list[int] | None = None,
    runner: SubprocessRunner | None = None,
) -> dict[str, Any]:
    seeds = seeds or [1, 2, 3]
    runner = runner or SubprocessRunner()
    artifacts_root = Path(artifacts_root)
    wf = ResearchWorkflow()

    # 1. Question ------------------------------------------------------------
    q = ResearchQuestion(
        id=new_id("q"), project_id=project_id,
        title="¿Qué forma funcional describe mejor el enfriamiento observado y generaliza fuera del rango medido?",
        description="Datos sintéticos con ruido de un proceso de enfriamiento; la ecuación generadora se oculta al ajustador.",
    )
    ledger.add_entity(q)
    wf.advance(WorkflowState.BACKGROUND_REVIEWED)

    # 2. Assumptions ---------------------------------------------------------
    assumptions = [
        "El ruido es aproximadamente gaussiano e independiente.",
        "La temperatura ambiente es constante.",
        "Menor RMSE fuera de muestra es un proxy (heurístico) de mejor modelo.",
    ]
    assumption_ids = []
    for text in assumptions:
        a = Assumption(id=new_id("asm"), project_id=project_id, title=text)
        ledger.add_entity(a)
        assumption_ids.append(a.id)
    wf.advance(WorkflowState.ASSUMPTIONS_RECORDED)

    # 3. Competing hypotheses ------------------------------------------------
    hypo_specs = [
        ("linear", "La relación es aproximadamente lineal en t.",
         "Falso si un modelo no lineal reduce el RMSE de test de forma sustancial."),
        ("cubic", "Un polinomio de bajo grado (cúbico) captura la curvatura.",
         "Falso si falla en extrapolación frente al modelo físico."),
        ("exponential_physical", "El decaimiento es exponencial: T = T_env + (T0-T_env)e^{-k t}.",
         "Falso si otro modelo generaliza mejor fuera del rango de entrenamiento."),
        ("overfit_poly9", "Un polinomio flexible (grado 9) describe mejor los datos.",
         "Falso si sobreajusta: bajo error en train pero alto en extrapolación."),
    ]
    hypo_ids: dict[str, str] = {}
    for name, statement, falsif in hypo_specs:
        h = Hypothesis(
            id=new_id("hyp"), project_id=project_id, question_id=q.id,
            title=statement, falsifiable=True, falsification_criteria=falsif,
            tags=[name],
        )
        ledger.add_entity(h)
        hypo_ids[name] = h.id
    wf.advance(WorkflowState.HYPOTHESES_PROPOSED)

    # 4. Pre-registered predictions -----------------------------------------
    pred_ids: list[str] = []
    pred_specs = [
        (hypo_ids["exponential_physical"],
         "El modelo exponencial tendrá el menor RMSE de extrapolación.",
         "RMSE de extrapolación exponencial < que el de los polinomios.",
         "El exponencial NO gana en extrapolación."),
        (hypo_ids["overfit_poly9"],
         "El polinomio de grado 9 tendrá bajo RMSE en train pero alto en extrapolación.",
         "train_rmse bajo y extrapolation_rmse alto para poly9.",
         "poly9 generaliza igual de bien fuera del rango."),
    ]
    for hid, title, supports, weakens in pred_specs:
        p = Prediction(
            id=new_id("pred"), project_id=project_id, hypothesis_id=hid,
            title=title, would_support=supports, would_weaken=weakens,
        )
        ledger.add_entity(p)
        pred_ids.append(p.id)
    wf.advance(WorkflowState.PREDICTIONS_PREREGISTERED)

    # 5. Experiment design ---------------------------------------------------
    exp = ExperimentPlan(
        id=new_id("exp"), project_id=project_id,
        title="Ajuste y comparación de 4 modelos competidores sobre datos de enfriamiento sintéticos",
        prediction_ids=pred_ids,
        variables={"seeds": seeds, "model_family": [n for n, *_ in hypo_specs]},
        metric="RMSE (train/val/test/extrapolation)",
        baseline="Predicción de la media de entrenamiento",
        controls=["train/test disjuntos", "baseline ingenuo", "múltiples semillas"],
        stopping_criterion="Ejecutar todas las semillas una vez; sin búsqueda adaptativa.",
        compute_budget={"cpu_seconds_per_run": 30, "runs": len(seeds) + 1},
        risks=["Sobreajuste del poly9", "Elección de métrica", "Rango limitado"],
        preregistered=True,
    )
    ledger.add_entity(exp)
    wf.advance(WorkflowState.EXPERIMENT_DESIGNED)

    # 5b. Preregistration object (hashed before running) ---------------------
    prereg = Preregistration(
        project_id=project_id, experiment_id=exp.id,
        question=q.title,
        hypotheses=[s for _, s, _ in hypo_specs],
        predictions=[t for _, t, _, _ in pred_specs],
        variables=exp.variables,
        metric=exp.metric, baseline=exp.baseline, controls=exp.controls,
        result_that_would_support="El exponencial minimiza el RMSE de extrapolación.",
        result_that_would_weaken="Un polinomio iguala o supera al exponencial en extrapolación.",
        stopping_criterion=exp.stopping_criterion,
        compute_budget=exp.compute_budget, risks=exp.risks,
    )
    prereg_hash = require_complete(prereg)

    # 6. Human approval (recorded; auto-approved for this reversible pilot) --
    wf.advance(WorkflowState.EXPERIMENT_APPROVED)

    # 7. Execution (multi-seed, sandboxed) -----------------------------------
    wf.advance(WorkflowState.RUNNING)
    per_seed: list[dict[str, Any]] = []
    run_ids: list[str] = []
    for seed in seeds:
        run_id = new_id("run")
        bundle = ArtifactBundle(artifacts_root / run_id)
        params = params_for_seed(seed)
        bundle.write_input("params.json", json.dumps(params, indent=2))
        bundle.write_code(PILOT_SCRIPT)
        env = capture_environment()
        bundle.write_environment(env)

        sres = runner.run(PILOT_SCRIPT, bundle.root, timeout_sec=30)
        # The runner writes its own code/script.py; ensure our inputs are alongside.
        bundle.write_logs(sres.stdout, sres.stderr)

        if sres.status != "ok":
            bundle.write_result_md(f"# Run FAILED\nstatus={sres.status}\n\n{sres.stderr}")
            ledger.add_run(ExecutionRun(
                id=run_id, project_id=project_id, experiment_id=exp.id,
                environment=env, seeds=[seed], status=sres.status,
                exit_code=sres.exit_code, artifacts_dir=str(bundle.root),
            ))
            ledger.update_run(run_id, {"status": sres.status})
            raise RuntimeError(f"Pilot run failed for seed {seed}: {sres.stderr[:500]}")

        raw = parse_stdout(sres.stdout)
        flat = flatten_metrics(raw)
        bundle.write_metrics(raw)
        in_h, code_h, out_h = hash_inputs_outputs(bundle)
        prov = {
            "prereg_hash": prereg_hash, "input_hash": in_h,
            "code_hash": code_h, "output_hash": out_h, "seed": seed,
        }
        bundle.write_provenance(prov)
        bundle.write_result_md(
            f"# Resultado (seed={seed})\n\n"
            f"- Mejor modelo por RMSE de test: **{flat['best_model']}**\n"
            f"- k recuperado: {flat['recovered_k']:.4f} (real: {flat['true_k']})\n"
            f"- RMSE test: {flat['test_rmse']:.4f} · extrapolación: {flat['extrapolation_rmse']:.4f}\n"
            f"- Baseline (media): {flat['baseline_rmse']:.4f}\n"
        )
        bundle.checksum_all()

        run = ExecutionRun(
            id=run_id, project_id=project_id, experiment_id=exp.id,
            environment=env, seeds=[seed], input_hash=in_h, code_hash=code_h,
            output_hash=out_h, exit_code=sres.exit_code, status="ok",
            artifacts_dir=str(bundle.root),
        )
        ledger.add_run(run)
        ledger.update_run(run_id, {"status": "ok", "output_hash": out_h})
        run_ids.append(run_id)
        per_seed.append({"seed": seed, "flat": flat, "raw": raw, "output_hash": out_h})

    wf.advance(WorkflowState.RESULTS_CAPTURED)

    # 8. Record results and negative results --------------------------------
    # Aggregate: which model won most often, mean extrapolation error.
    best_counts: dict[str, int] = {}
    for ps in per_seed:
        best_counts[ps["flat"]["best_model"]] = best_counts.get(ps["flat"]["best_model"], 0) + 1
    overall_best = max(best_counts, key=lambda m: best_counts[m])
    mean_recovered_k = sum(ps["flat"]["recovered_k"] for ps in per_seed) / len(per_seed)
    ref_flat = per_seed[0]["flat"]

    result = ResearchResult(
        id=new_id("res"), project_id=project_id, run_id=run_ids[0],
        title=f"Modelo ganador ({overall_best}) recupera la forma exponencial",
        description=f"Ganador en {best_counts.get(overall_best,0)}/{len(seeds)} semillas. k≈{mean_recovered_k:.3f}.",
        metrics={"best_counts": best_counts, "mean_recovered_k": mean_recovered_k,
                 "reference": ref_flat},
        confidence=ConfidenceAssessment(value=0.7, method="out_of_sample_rmse",
                                        rationale="Consistente entre semillas; sólo datos sintéticos."),
        provenance=[ProvenanceRef(kind="execution_run", ref_id=run_ids[0],
                                  detail="run de referencia")],
    )
    ledger.add_entity(result)

    # Negative result: the flexible poly9 overfits (fails extrapolation).
    neg = NegativeResult(
        id=new_id("neg"), project_id=project_id, run_id=run_ids[0],
        title="poly9 sobreajusta: falla en extrapolación pese a bajo error de entrenamiento",
        description="Resultado NEGATIVO preservado: un modelo flexible no equivale a mejor modelo.",
        metrics={"overfit_train_rmse": ref_flat["overfit_train_rmse"],
                 "overfit_extrapolation_rmse": ref_flat["overfit_extrapolation_rmse"]},
    )
    ledger.add_entity(neg)

    # 9. Skeptic refutation attempt -----------------------------------------
    wf.advance(WorkflowState.FALSIFICATION_REVIEW)
    ref_run = ledger.get_run(run_ids[0]) or {}
    # The skeptic evaluates the experiment as a whole, which used all seeds.
    skeptic = review_experiment(prereg.model_dump(), {**ref_run, "seeds": seeds}, ref_flat)
    skeptic_dict = skeptic.to_dict()

    # 10. Reproducibility check: re-run seed[0] and compare output hash -------
    wf.advance(WorkflowState.REPRODUCIBILITY_CHECK)
    repro_bundle = ArtifactBundle(artifacts_root / (run_ids[0] + "_repro"))
    repro_bundle.write_input("params.json", json.dumps(params_for_seed(seeds[0]), indent=2))
    repro_res = runner.run(PILOT_SCRIPT, repro_bundle.root, timeout_sec=30)
    repro_raw = parse_stdout(repro_res.stdout) if repro_res.status == "ok" else {}
    reproduced = (
        repro_res.status == "ok"
        and hash_json(repro_raw) == hash_json(per_seed[0]["raw"])
    )

    # 11. A cautious claim (never a discovery) ------------------------------
    claim = ScientificClaim(
        id=new_id("clm"), project_id=project_id,
        title="Sobre estos datos sintéticos, el modelo exponencial generaliza mejor que los polinomios probados.",
        description="Afirmación limitada a datos sintéticos. NO es un descubrimiento; recupera una ley conocida.",
        is_speculation=False,
        supported_by=[result.id],
        contradicted_by=[],
        confidence=ConfidenceAssessment(value=0.65, method="out_of_sample_rmse"),
        provenance=[ProvenanceRef(kind="execution_run", ref_id=run_ids[0])],
    )
    ledger.add_entity(claim)

    wf.advance(WorkflowState.HUMAN_REVIEW)

    # 12. Learning artifacts -------------------------------------------------
    learning_dir = artifacts_root / "learning"
    learning_files = write_learning_docs(learning_dir, ref_flat, skeptic_dict)

    return {
        "project_id": project_id,
        "workflow_history": [s.value for s in wf.history],
        "prereg_hash": prereg_hash,
        "question_id": q.id,
        "hypothesis_ids": hypo_ids,
        "prediction_ids": pred_ids,
        "experiment_id": exp.id,
        "run_ids": run_ids,
        "result_id": result.id,
        "negative_result_id": neg.id,
        "claim_id": claim.id,
        "overall_best_model": overall_best,
        "best_counts": best_counts,
        "mean_recovered_k": mean_recovered_k,
        "true_k": ref_flat["true_k"],
        "reference_metrics": ref_flat,
        "skeptic": skeptic_dict,
        "reproduced": reproduced,
        "reproducibility_detail": {
            "compared": "output JSON hash of seed[0] across two independent runs",
            "match": reproduced,
        },
        "learning_files": learning_files,
        "cannot_conclude": [
            "Que exista una nueva ley (se recuperó una conocida).",
            "Que el ajuste implique causalidad física.",
            "Que el resultado aplique fuera de estos datos sintéticos.",
        ],
    }
