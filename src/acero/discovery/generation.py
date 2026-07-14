"""Structured hypothesis generation (Sprint 5.2).

Two generators behind one interface:
  * MockHypothesisGenerator — deterministic, offline, produces a scientifically
    DIVERSE set of competing hypotheses (linear, polynomial, exponential,
    logistic, damped oscillator, flexible, null, baseline). Used in tests and when
    no LLM is selected; keeps the whole Discovery Engine runnable without cost.
  * CodexHypothesisGenerator — uses ``provider.complete_json`` with a strict schema
    so Codex must return several genuinely competing hypotheses, not cosmetic
    variants. Records full generation provenance (provider/model/params/tokens).

Rule: sources returned by an LLM are recorded as *claimed* (``sources_verified =
False``) and never become evidence.
"""

from __future__ import annotations

import json
from typing import Any

from ..core.ids import new_id
from .candidates import (
    CandidateStatus,
    GenerationProvenance,
    HypothesisCandidate,
    HypothesisType,
)

HYPOTHESIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "hypothesis_type": {
                        "type": "string",
                        "enum": [t.value for t in HypothesisType],
                    },
                    "mechanism": {"type": "string"},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                    "predicted_observations": {"type": "array", "items": {"type": "string"}},
                    "falsification_conditions": {"type": "array", "items": {"type": "string"}},
                    "required_variables": {"type": "array", "items": {"type": "string"}},
                    "differs_from_others": {"type": "string"},
                    "supporting_evidence_kind": {"type": "string"},
                    "weakening_evidence_kind": {"type": "string"},
                },
                # Codex --output-schema (OpenAI structured outputs) requires EVERY
                # property to appear in "required".
                "required": [
                    "title", "statement", "hypothesis_type", "mechanism",
                    "assumptions", "predicted_observations", "falsification_conditions",
                    "required_variables", "differs_from_others",
                    "supporting_evidence_kind", "weakening_evidence_kind",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["hypotheses"],
    "additionalProperties": False,
}

_PROMPT = """You are a scientific hypothesis generator. For the research question below,
produce {n} COMPETING, falsifiable hypotheses that differ in MECHANISM, not just in
wording or parameters. Include at least: one null/baseline hypothesis, one
physically/mathematically motivated mechanism, one alternative mechanism, and one
flexible model prone to overfitting.

For each hypothesis give: title, statement, hypothesis_type, mechanism, assumptions,
predicted_observations (concrete/measurable), falsification_conditions, and
required_variables. Do NOT invent citations. Return JSON only, matching the schema.

Research question:
{question}

Context (variables/data available):
{context}"""


# --- deterministic mock templates -------------------------------------------
def _mock_templates(variables: list[str]) -> list[dict[str, Any]]:
    v = variables[0] if variables else "t"
    y = variables[1] if len(variables) > 1 else "y"
    return [
        {
            "title": "Linear trend", "hypothesis_type": HypothesisType.PREDICTIVE,
            "statement": f"{y} is an approximately linear function of {v}.",
            "mechanism": "constant rate of change; straight-line relationship",
            "assumptions": ["no curvature", "homoscedastic noise"],
            "predicted_observations": [f"{y} increases/decreases proportionally with {v}",
                                       "residuals show no curvature"],
            "falsification_conditions": ["a nonlinear model reduces test RMSE substantially"],
        },
        {
            "title": "Cubic polynomial", "hypothesis_type": HypothesisType.PREDICTIVE,
            "statement": f"{y} follows a low-order (cubic) polynomial in {v}.",
            "mechanism": "polynomial curvature captured by a degree-3 fit",
            "assumptions": ["smoothness", "no regime change"],
            "predicted_observations": [f"cubic fit tracks {y} within noise on the training range"],
            "falsification_conditions": ["fails extrapolation vs a mechanistic model"],
        },
        {
            "title": "Exponential decay/growth", "hypothesis_type": HypothesisType.MECHANISTIC,
            "statement": f"{y} changes exponentially: rate proportional to a gap.",
            "mechanism": "exponential relaxation toward an asymptote (dy/dt = -k(y - y_inf))",
            "assumptions": ["constant rate constant k", "single time-scale"],
            "predicted_observations": [f"{y} approaches an asymptote", "log-residual is linear"],
            "falsification_conditions": ["a non-exponential model generalises better out of range"],
        },
        {
            "title": "Logistic saturation", "hypothesis_type": HypothesisType.MECHANISTIC,
            "statement": f"{y} follows logistic growth with a carrying capacity.",
            "mechanism": "logistic ODE dy/dt = r y (1 - y/K); S-shaped saturation",
            "assumptions": ["fixed carrying capacity K", "density-dependent rate"],
            "predicted_observations": ["S-shaped curve", "inflection at K/2"],
            "falsification_conditions": ["no inflection observed; exponential fits better"],
        },
        {
            "title": "Damped oscillation", "hypothesis_type": HypothesisType.MECHANISTIC,
            "statement": f"{y} oscillates with decaying amplitude.",
            "mechanism": "damped harmonic oscillator: restoring force + friction",
            "assumptions": ["linear restoring force", "viscous damping"],
            "predicted_observations": ["oscillatory residuals", "decaying peak amplitude"],
            "falsification_conditions": ["no oscillation in residuals across seeds"],
        },
        {
            "title": "Flexible high-degree polynomial", "hypothesis_type": HypothesisType.COMPUTATIONAL,
            "statement": f"{y} is best described by a flexible degree-9 polynomial in {v}.",
            "mechanism": "flexible over-parameterised polynomial (poly9)",
            "assumptions": ["enough data to constrain 10 coefficients"],
            "predicted_observations": ["very low training error"],
            "falsification_conditions": ["extrapolation RMSE explodes vs mechanistic model"],
        },
        {
            "title": "Null: no structure", "hypothesis_type": HypothesisType.NULL,
            "statement": f"{y} has no systematic dependence on {v} beyond noise.",
            "mechanism": "constant mean; variation is noise",
            "assumptions": ["stationary noise"],
            "predicted_observations": ["mean predictor is not beaten significantly"],
            "falsification_conditions": ["any model beats the mean baseline on test"],
        },
        {
            "title": "Baseline: mean predictor", "hypothesis_type": HypothesisType.BASELINE,
            "statement": f"Predict {y} as the training mean regardless of {v}.",
            "mechanism": "naive baseline (training mean)",
            "assumptions": [],
            "predicted_observations": ["baseline RMSE equals data standard deviation"],
            "falsification_conditions": ["trivially superseded by any structured model"],
        },
    ]


def _make_candidate(project_id: str, rq_id: str, spec: dict[str, Any],
                    variables: list[str], gen: GenerationProvenance) -> HypothesisCandidate:
    htype = spec["hypothesis_type"]
    if isinstance(htype, str):
        htype = HypothesisType(htype)
    return HypothesisCandidate(
        id=new_id("hc"), research_question_id=rq_id, project_id=project_id,
        title=spec["title"], statement=spec["statement"], hypothesis_type=htype,
        mechanism=spec.get("mechanism", ""),
        assumptions=list(spec.get("assumptions", [])),
        predicted_observations=list(spec.get("predicted_observations", [])),
        falsification_conditions=list(spec.get("falsification_conditions", [])),
        required_variables=list(spec.get("required_variables", variables)),
        estimated_compute={"cpu_seconds": 5},
        scientific_rationale=spec.get("differs_from_others", ""),
        status=CandidateStatus.PROPOSED, generation=gen, sources_verified=False,
    )


class MockHypothesisGenerator:
    name = "mock"

    def generate(self, question: str, *, project_id: str, research_question_id: str,
                 context: dict[str, Any] | None = None, n: int = 8) -> list[HypothesisCandidate]:
        context = context or {}
        variables = context.get("variables", ["t", "y"])
        gen = GenerationProvenance(generator="mock", provider="mock", model="mock-1",
                                   prompt_version="v1", params={"n": n})
        specs = _mock_templates(variables)[:max(n, 1)]
        return [_make_candidate(project_id, research_question_id, s, variables, gen)
                for s in specs]


class CodexHypothesisGenerator:
    name = "codex"

    def __init__(self, provider: Any, prompt_version: str = "v1") -> None:
        self.provider = provider
        self.prompt_version = prompt_version

    def generate(self, question: str, *, project_id: str, research_question_id: str,
                 context: dict[str, Any] | None = None, n: int = 8) -> list[HypothesisCandidate]:
        if not hasattr(self.provider, "complete_json"):
            raise TypeError("Codex generator requires a provider with complete_json")
        context = context or {}
        variables = context.get("variables", ["t", "y"])
        prompt = _PROMPT.format(n=n, question=question,
                                context=json.dumps(context, ensure_ascii=False))
        result = self.provider.complete_json(prompt, HYPOTHESIS_JSON_SCHEMA)
        gen = GenerationProvenance(
            generator="codex", provider=getattr(self.provider, "name", "codex"),
            model=getattr(self.provider, "model", None) or "codex-default",
            prompt_version=self.prompt_version,
            params={"n": n},
            token_usage=getattr(self.provider, "last_usage", {}) or {},
        )
        out: list[HypothesisCandidate] = []
        for spec in result.get("hypotheses", []):
            try:
                out.append(_make_candidate(project_id, research_question_id, spec, variables, gen))
            except Exception:  # noqa: BLE001 - skip malformed items, keep the rest
                continue
        return out
