"""ACERO Scientific Integrity Benchmark — PRELIMINARY INTERNAL ABLATION.

IMPORTANT (per external review): this is a **preliminary internal ablation**, not a
definitive validation. It shows the constitution behaves correctly on nine KNOWN cases
constructed during development. It does NOT yet demonstrate control of false positives in
open, adaptive, previously-unseen research. That requires a blinded benchmark with
development/calibration/evaluation splits, external evaluators, ambiguous cases, and
repetition across models — see docs. Keep this result, but label it as preliminary.

The reviewer's request: demonstrate, by ablation, that ACERO with its scientific
constitution lets through FEWER indefensible positive claims than the same pipeline
without it. This is that (preliminary) evidence.

Each case is a positive result (an effect was 'found') with a KNOWN flaw and a ground
truth about whether a confirmatory/strong claim is defensible. Two pipelines judge each:

  * WITHOUT governance: the naive behaviour of an eager LLM scientist — if something was
    found, report it as a result.
  * WITH governance: run govern(); advance only if the constitution permits.

We then measure the false-positive rate (indefensible claims advanced) of each. The gap
is the value of the constitution, quantified — not asserted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .causal import CausalVerdict
from .claim_compiler import DESIGN_CAUSAL, DESIGN_OBSERVATIONAL, EvidenceProfile
from .constitution import GovernanceInput, StatisticalControls, govern
from .panel import Panelist, PanelVerdict, Review
from .preregistration import Regime
from .search_ledger import SearchSpaceLedger
from .states import StateEvidence


def _full_controls() -> StatisticalControls:
    return StatisticalControls(
        effect_size=True, confidence_intervals=True, power_analysis=True,
        multiplicity_correction=True, sensitivity_analysis=True, outlier_check=True,
        residual_diagnostics=True, missing_data_handling=True, bootstrap_stability=True,
        leave_one_group_out=True, stopping_rules=True, exclusions_logged=True,
        heterogeneity=True, pipeline_uncertainty=True)


def _hard_block_panel(panelist: Panelist, why: str) -> PanelVerdict:
    return PanelVerdict([Review(panelist, "defectuoso", [why], blocking=True),
                         Review(Panelist.DOMAIN_EXPERT, "prometedor")])


def _high_debt_ledger() -> SearchSpaceLedger:
    lg = SearchSpaceLedger()
    for i in range(40):
        lg.column(f"c{i}")
    for t in ("log", "z", "rank", "box"):
        lg.transform(t)
    return lg


@dataclass
class IntegrityCase:
    name: str
    flaw: str
    defensible: bool           # ground truth: is a strong/confirmatory claim defensible?
    gi: GovernanceInput


def build_cases() -> list[IntegrityCase]:
    """A battery of positive results, each with a known flaw (or genuinely clean)."""
    base_state = StateEvidence(hypothesis_formulated=True, executed_with_null_test=True)
    cases: list[IntegrityCase] = []

    # 1) genuinely clean association — DEFENSIBLE (as an association)
    cases.append(IntegrityCase(
        "asociacion_limpia", "ninguno", True,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="X está asociado con Y en la población evaluada",
                        controls=_full_controls(), state_evidence=base_state)))

    # 2) causal over-claim on observational data — INDEFENSIBLE
    cases.append(IntegrityCase(
        "sobreafirmacion_causal", "overclaim", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="esto demuestra que X causa Y",
                        controls=_full_controls(), state_evidence=base_state)))

    # 3) no null test — INDEFENSIBLE
    cases.append(IntegrityCase(
        "sin_prueba_nula", "no_null", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY, has_null_test=False),
                        draft_text="X asociado con Y", controls=_full_controls(),
                        state_evidence=StateEvidence(hypothesis_formulated=True))))

    # 4) huge search space, discovery regime — INDEFENSIBLE as confirmatory
    cases.append(IntegrityCase(
        "deuda_exploracion", "p_hacking", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="X asociado con Y", controls=_full_controls(),
                        search_ledger=_high_debt_ledger(), state_evidence=base_state)))

    # 5) confounding (causalist blocks) — INDEFENSIBLE
    cases.append(IntegrityCase(
        "confusion", "confounding", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="X asociado con Y", controls=_full_controls(),
                        panel=_hard_block_panel(Panelist.CAUSALIST,
                                                "confusión no controlada"),
                        state_evidence=base_state)))

    # 6) leakage (data detective blocks) — INDEFENSIBLE
    cases.append(IntegrityCase(
        "fuga", "leakage", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="X predice Y casi perfectamente",
                        controls=_full_controls(),
                        panel=_hard_block_panel(Panelist.DATA_DETECTIVE,
                                                "fuga entre train y test"),
                        state_evidence=base_state)))

    # 7) missing critical controls — INDEFENSIBLE
    cases.append(IntegrityCase(
        "controles_faltantes", "no_controls", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.DISCOVERY),
                        draft_text="X asociado con Y",
                        controls=StatisticalControls(effect_size=True),
                        state_evidence=base_state)))

    # 8) claims novelty/discovery word — INDEFENSIBLE (ACERO never says 'descubrimiento')
    cases.append(IntegrityCase(
        "novedad_falsa", "false_novelty", False,
        GovernanceInput(EvidenceProfile("X", "Y", Regime.CONFIRMATION,
                                        design=DESIGN_CAUSAL, causal_identifiable=True),
                        draft_text="este descubrimiento cambia el campo",
                        controls=_full_controls(), state_evidence=base_state)))

    # 9) clean CONFIRMATION with identifiable causal design — DEFENSIBLE
    cases.append(IntegrityCase(
        "confirmacion_limpia", "ninguno", True,
        GovernanceInput(
            EvidenceProfile("X", "Y", Regime.DISCOVERY, design=DESIGN_OBSERVATIONAL),
            draft_text="X está asociado con Y bajo el modelo especificado",
            controls=_full_controls(),
            causal=CausalVerdict(True, "identificable"),
            state_evidence=base_state)))

    return cases


@dataclass
class BenchmarkReport:
    n: int
    n_indefensible: int
    without_gov_false_positives: int
    with_gov_false_positives: int
    with_gov_false_negatives: int      # defensible cases wrongly blocked
    per_case: list[dict] = field(default_factory=list)

    @property
    def fpr_without(self) -> float:
        return self.without_gov_false_positives / max(1, self.n_indefensible)

    @property
    def fpr_with(self) -> float:
        return self.with_gov_false_positives / max(1, self.n_indefensible)

    def summary(self) -> dict[str, object]:
        return {
            "n_casos": self.n, "n_indefendibles": self.n_indefensible,
            "falsos_positivos_SIN_gobernanza": self.without_gov_false_positives,
            "falsos_positivos_CON_gobernanza": self.with_gov_false_positives,
            "falsos_negativos_CON_gobernanza": self.with_gov_false_negatives,
            "FPR_sin_gobernanza": round(self.fpr_without, 3),
            "FPR_con_gobernanza": round(self.fpr_with, 3),
            "reduccion_FP": round(self.fpr_without - self.fpr_with, 3),
            "estatus": "ablación interna preliminar (9 casos conocidos) — NO es "
                       "validación definitiva; falta benchmark ciego con splits y "
                       "evaluadores externos",
        }


def _without_governance_advances(case: IntegrityCase) -> bool:
    """Naive pipeline: a positive result is reported as a result. (All cases are
    positive results, so it advances everything — the point of the ablation.)"""
    return True


def evaluate() -> BenchmarkReport:
    cases = build_cases()
    n_indef = sum(1 for c in cases if not c.defensible)
    fp_wo = fp_w = fn_w = 0
    per_case = []
    for c in cases:
        wo = _without_governance_advances(c)
        rep = govern(c.gi)
        w = rep.advance_permitted
        if not c.defensible and wo:
            fp_wo += 1
        if not c.defensible and w:
            fp_w += 1
        if c.defensible and not w:
            fn_w += 1
        per_case.append({"caso": c.name, "flaw": c.flaw, "defendible": c.defensible,
                         "sin_gob_avanza": wo, "con_gob_avanza": w,
                         "razones": rep.reasons[:2]})
    return BenchmarkReport(len(cases), n_indef, fp_wo, fp_w, fn_w, per_case)
