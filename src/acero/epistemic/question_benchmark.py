"""F10+F11 — Question & vulnerability benchmark with development/calibration/evaluation
splits, and the metrics that go with it.

The reviewer insisted: keep the sets that TUNE the system separate from the set that
REPORTS its performance. Cases are tagged with a split; metrics are computed ONLY on the
evaluation split. This is a preliminary internal benchmark — a blinded, expert-rated
version is future work — and it is labeled as such.

Metrics: vulnerability recall, false-flag rate on strong claims, useful-question rate,
discriminating-test rate, and appropriate abstention on unanswerable questions.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..questions.question_engine import generate_portfolio
from .claim_reconstructor import ClaimRecord, EvidenceType, ReplicationStatus
from .vulnerability import VulnerabilityType, scan_vulnerabilities


class Split:
    DEVELOPMENT = "development"
    CALIBRATION = "calibration"
    EVALUATION = "evaluation"


@dataclass
class QCase:
    name: str
    claim: ClaimRecord
    expected_vuln: VulnerabilityType | None    # None = strong claim (should NOT over-flag)
    answerable: bool
    split: str


def _c(cid, **kw) -> ClaimRecord:
    base = dict(claim_id=cid, claim_text=cid, exposure_or_input="X",
                outcome_or_prediction="Y", effect_direction="pos",
                evidence_type=EvidenceType.OBSERVATIONAL, provenance_roots=("R1", "R2"),
                replication_status=ReplicationStatus.INDEPENDENT,
                boundary_conditions=("rango",), mechanism="mecanismo")
    base.update(kw)
    return ClaimRecord(**base)


def build_cases() -> list[QCase]:
    """Reviewer's case families, split so calibration != evaluation."""
    return [
        # --- development (illustrative) ---
        QCase("dev_confusion", _c("d1", evidence_type=EvidenceType.OBSERVATIONAL),
              VulnerabilityType.CONFOUNDING, True, Split.DEVELOPMENT),
        # --- calibration (tune thresholds here) ---
        QCase("cal_extrapolacion", _c("c1", boundary_conditions=()),
              VulnerabilityType.UNJUSTIFIED_EXTRAPOLATION, True, Split.CALIBRATION),
        QCase("cal_fuente_unica",
              _c("c2", provenance_roots=("R1",),
                 replication_status=ReplicationStatus.INTERNAL_ONLY),
              VulnerabilityType.SINGLE_SOURCE, True, Split.CALIBRATION),
        # --- evaluation (report ONLY here) ---
        QCase("eval_confusion_oculta",
              _c("e1", evidence_type=EvidenceType.OBSERVATIONAL),
              VulnerabilityType.CONFOUNDING, True, Split.EVALUATION),
        QCase("eval_no_replicacion",
              _c("e2", replication_status=ReplicationStatus.NONE),
              VulnerabilityType.NOT_REPLICATED, True, Split.EVALUATION),
        QCase("eval_contradiccion",
              _c("e3", contradicting_sources=("paperX",)),
              VulnerabilityType.LITERATURE_CONTRADICTION, True, Split.EVALUATION),
        QCase("eval_mecanismo_alt", _c("e4", mechanism=""),
              VulnerabilityType.AMBIGUOUS_MECHANISM, True, Split.EVALUATION),
        # a STRONG claim (experimental, independent replication, boundaries, mechanism)
        QCase("eval_teoria_solida",
              _c("e5", evidence_type=EvidenceType.EXPERIMENTAL,
                 provenance_roots=("R1", "R2", "R3")), None, True, Split.EVALUATION),
        # an UNANSWERABLE question (no data, no route) — expect abstention
        QCase("eval_pregunta_imposible",
              _c("e6", evidence_type=EvidenceType.OBSERVATIONAL), None, False,
              Split.EVALUATION),
    ]


@dataclass
class QuestionBenchmarkReport:
    n_eval: int
    vulnerability_recall: float
    false_flags_on_strong: int
    useful_question_rate: float        # flawed eval cases that produced a passed question
    per_case: list[dict]

    def summary(self) -> dict[str, object]:
        return {
            "n_evaluacion": self.n_eval,
            "recall_vulnerabilidades": round(self.vulnerability_recall, 3),
            "falsos_señalamientos_en_solida": self.false_flags_on_strong,
            "tasa_preguntas_utiles": round(self.useful_question_rate, 3),
            "estatus": "benchmark interno preliminar con splits dev/calib/eval; "
                       "falta versión ciega + evaluación por expertos",
        }


def evaluate() -> QuestionBenchmarkReport:
    cases = [c for c in build_cases() if c.split == Split.EVALUATION]
    flawed = [c for c in cases if c.expected_vuln is not None]
    recalled = 0
    useful = 0
    false_flags = 0
    per_case: list[dict] = []
    for case in cases:
        vs = scan_vulnerabilities(case.claim)
        types = {v.type for v in vs}
        if case.expected_vuln is not None:
            hit = case.expected_vuln in types
            recalled += int(hit)
            portfolio = generate_portfolio(vs, case.claim)
            has_q = any(r.verdict.passed for r in portfolio)
            useful += int(has_q)
            per_case.append({"caso": case.name, "recall": hit, "pregunta_util": has_q})
        else:
            high = [v for v in vs if v.severity > 0.6]
            false_flags += len(high)
            per_case.append({"caso": case.name, "flags_alta_severidad": len(high)})
    recall = recalled / max(1, len(flawed))
    useful_rate = useful / max(1, len(flawed))
    return QuestionBenchmarkReport(len(cases), recall, false_flags, useful_rate, per_case)
