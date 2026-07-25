"""Scientific Question Engine — turn epistemic vulnerabilities into fertile questions.

The reviewer's key demand: the engine must not produce a list of pretty questions ordered
by how surprising they sound. It must produce INVESTIGABLE, FALSIFIABLE, PRIORITIZED
questions, each LINKED to a concrete gap (a vulnerability), each scored on a transparent,
multidimensional card whose components are always shown (never hidden in a single number).

A question is blocked if it cannot be refuted, merely restates a conclusion, is ambiguous,
would change no belief, needs nonexistent data with no experimental route, confuses
association with causation, is already solidly answered, or is novel-but-trivial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..epistemic.claim_reconstructor import ClaimRecord
from ..epistemic.vulnerability import EpistemicVulnerability, VulnerabilityType


class QuestionFamily(str, Enum):
    CONTRADICTION = "contradiccion"
    BOUNDARY = "frontera"
    MECHANISM = "mecanismo"
    METHOD_DEPENDENCE = "dependencia_metodologica"
    TRANSPORTABILITY = "transportabilidad"
    ANOMALY = "anomalia"
    MISSING_EVIDENCE = "evidencia_faltante"
    RIVAL_THEORY = "teoria_rival"
    NEGATIVE_RESULT = "resultado_negativo"


_VULN_TO_FAMILY = {
    VulnerabilityType.SINGLE_SOURCE: QuestionFamily.TRANSPORTABILITY,
    VulnerabilityType.NOT_REPLICATED: QuestionFamily.TRANSPORTABILITY,
    VulnerabilityType.CONFOUNDING: QuestionFamily.METHOD_DEPENDENCE,
    VulnerabilityType.REVERSE_CAUSATION: QuestionFamily.MECHANISM,
    VulnerabilityType.UNJUSTIFIED_EXTRAPOLATION: QuestionFamily.BOUNDARY,
    VulnerabilityType.LIMITED_RANGE: QuestionFamily.BOUNDARY,
    VulnerabilityType.AMBIGUOUS_MECHANISM: QuestionFamily.RIVAL_THEORY,
    VulnerabilityType.LITERATURE_CONTRADICTION: QuestionFamily.CONTRADICTION,
    VulnerabilityType.UNVALIDATED_ASSUMPTION: QuestionFamily.METHOD_DEPENDENCE,
    VulnerabilityType.IGNORED_RESIDUAL_ANOMALY: QuestionFamily.ANOMALY,
    VulnerabilityType.UNMEASURED_VARIABLES: QuestionFamily.MISSING_EVIDENCE,
}


@dataclass
class ScientificQuestion:
    question_id: str
    question_text: str
    family: QuestionFamily
    origin: str                     # "vulnerability:<id>" | "human" | "anomaly"
    target_vulnerability: str
    known_context: str = ""
    unknown: str = ""
    why_it_matters: str = ""
    competing_answers: tuple[str, ...] = ()
    required_data: str = ""
    status: str = "proposed"


@dataclass
class ScientificQuestionCard:
    """Every dimension in [0,1]. NEVER collapsed into a single opaque score."""
    clarity: float = 0.5
    falsifiability: float = 0.5
    bibliographic_novelty: float = 0.5
    scientific_novelty: float = 0.5
    importance: float = 0.5
    discriminating_power: float = 0.5
    data_availability: float = 0.5
    independence_potential: float = 0.5
    confounding_risk: float = 0.5
    computational_cost: float = 0.3
    experimental_cost: float = 0.3
    negative_result_value: float = 0.5
    mechanistic_impact: float = 0.5
    transportability: float = 0.5
    uncertainty: float = 0.5

    def components(self) -> dict[str, float]:
        return {k: round(float(v), 3) for k, v in vars(self).items()}

    def priority(self) -> float:
        """Transparent formula: expected value × discrimination × feasibility ×
        independence × negative-value ÷ residual epistemic risk. Components are shown."""
        sci_value = self.importance * (0.5 + 0.5 * self.scientific_novelty)
        feasibility = self.data_availability * (1.0 - 0.5 * (self.computational_cost
                                                             + self.experimental_cost) / 2)
        residual_risk = 1.0 + self.confounding_risk + self.uncertainty  # ≥1, never /0
        num = (sci_value * self.discriminating_power * max(feasibility, 0.01)
               * (0.5 + 0.5 * self.independence_potential)
               * (0.5 + 0.5 * self.negative_result_value))
        return num / residual_risk

    def report(self) -> dict[str, object]:
        return {"priority": round(self.priority(), 4), "components": self.components()}


@dataclass
class QualityVerdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def quality_gate(q: ScientificQuestion, card: ScientificQuestionCard) -> QualityVerdict:
    """Block questions that are not worth operational priority. Returns why."""
    reasons: list[str] = []
    if card.falsifiability < 0.35:
        reasons.append("no falsable: no se puede refutar")
    if card.clarity < 0.35:
        reasons.append("ambigua: definición inestable")
    if card.scientific_novelty < 0.15 and card.bibliographic_novelty < 0.15:
        reasons.append("ya respondida / reformulación de una conclusión conocida")
    if card.importance < 0.2:
        reasons.append("no cambiaría ninguna creencia (trivial), aunque sea novedosa")
    if card.data_availability < 0.1 and card.experimental_cost > 0.9:
        reasons.append("requiere datos inexistentes sin ruta experimental")
    if q.family is QuestionFamily.MECHANISM and card.discriminating_power < 0.2:
        reasons.append("confunde asociación con causalidad sin poder discriminante")
    return QualityVerdict(not reasons, reasons)


def question_from_vulnerability(vuln: EpistemicVulnerability, claim: ClaimRecord,
                                qid: str = "") -> ScientificQuestion:
    """Build a question TARGETED at a vulnerability (never a generic prompt)."""
    fam = _VULN_TO_FAMILY.get(vuln.type, QuestionFamily.MISSING_EVIDENCE)
    templates = {
        QuestionFamily.TRANSPORTABILITY:
            f"¿El efecto '{claim.effect_direction or 'observado'}' entre "
            f"{claim.exposure_or_input or 'la exposición'} y "
            f"{claim.outcome_or_prediction or 'el outcome'} se reproduce en una fuente de "
            f"raíz de curación INDEPENDIENTE?",
        QuestionFamily.METHOD_DEPENDENCE:
            "¿El efecto sobrevive al ajustar por el confusor candidato o al cambiar la "
            "definición del endpoint/preprocesamiento?",
        QuestionFamily.MECHANISM:
            "¿Qué predicción EXCLUSIVA distingue el mecanismo propuesto de la causalidad "
            "inversa u otro tercer factor?",
        QuestionFamily.BOUNDARY:
            "¿En qué rango/población deja de conservarse la relación observada?",
        QuestionFamily.RIVAL_THEORY:
            "¿Qué observación distinguiría inequívocamente los mecanismos rivales que "
            "producen este mismo patrón?",
        QuestionFamily.CONTRADICTION:
            "¿Qué diferencia de método o población explica el desacuerdo entre los "
            "estudios contradictorios, al armonizarlos?",
        QuestionFamily.ANOMALY:
            "¿Los residuos contienen una estructura no explicada que sea señal y no ruido?",
        QuestionFamily.MISSING_EVIDENCE:
            "¿Qué se descubriría al cruzar fuentes independientes por una entidad "
            "normalizada que nadie ha combinado?",
    }
    return ScientificQuestion(
        question_id=qid or f"q.{vuln.vulnerability_id}",
        question_text=templates.get(fam, "¿Qué evidencia reduciría esta incertidumbre?"),
        family=fam, origin=f"vulnerability:{vuln.vulnerability_id}",
        target_vulnerability=vuln.vulnerability_id,
        known_context=claim.normalized_claim or claim.claim_text[:120],
        unknown=vuln.possible_failure_mode,
        why_it_matters=vuln.description,
        competing_answers=vuln.alternative_explanations,
        required_data=vuln.required_data,
    )


def card_from(vuln: EpistemicVulnerability, claim: ClaimRecord) -> ScientificQuestionCard:
    """Heuristic card seeded from the vulnerability + claim (transparent, adjustable)."""
    return ScientificQuestionCard(
        clarity=0.7,
        falsifiability=0.4 + 0.5 * vuln.testability,
        bibliographic_novelty=0.5,
        scientific_novelty=0.35 + 0.3 * vuln.severity,
        importance=0.3 + 0.5 * vuln.severity,
        discriminating_power=vuln.testability,
        data_availability=0.6 if vuln.required_data else 0.4,
        independence_potential=0.7 if vuln.type in (
            VulnerabilityType.SINGLE_SOURCE, VulnerabilityType.NOT_REPLICATED) else 0.4,
        confounding_risk=0.6 if vuln.type in (
            VulnerabilityType.CONFOUNDING, VulnerabilityType.REVERSE_CAUSATION) else 0.3,
        negative_result_value=0.6,
        mechanistic_impact=0.6 if vuln.type == VulnerabilityType.AMBIGUOUS_MECHANISM else 0.4,
        transportability=0.6,
        uncertainty=vuln.uncertainty,
    )


@dataclass
class RankedQuestion:
    question: ScientificQuestion
    card: ScientificQuestionCard
    verdict: QualityVerdict

    @property
    def priority(self) -> float:
        return self.card.priority() if self.verdict.passed else 0.0


def generate_portfolio(vulns: list[EpistemicVulnerability], claim: ClaimRecord
                       ) -> list[RankedQuestion]:
    """From a vulnerability surface, produce a prioritized, quality-gated question set."""
    ranked: list[RankedQuestion] = []
    for v in vulns:
        q = question_from_vulnerability(v, claim)
        card = card_from(v, claim)
        ranked.append(RankedQuestion(q, card, quality_gate(q, card)))
    ranked.sort(key=lambda r: -r.priority)
    return ranked
