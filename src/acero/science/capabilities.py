"""Capa de capacidades tipadas — los personajes son la INTERFAZ, no la arquitectura.

Crítica del revisor externo (2026-08-10), aceptada: sin esta capa, en dos años
serían 18 agentes × herramientas × prompts × estados y nadie sabría quién es
responsable de qué. El Consejo sigue viéndose igual en la UI; por debajo:

    PERSONA → CAPABILITY → TOOL(módulo real) → EVIDENCE(kind del ledger)

Este registro es la fuente de verdad de esa correspondencia. Los tests fijan que
todo ejecutor de Bohr tiene capacidad declarada y que ninguna capacidad queda
huérfana — la deuda arquitectónica se detecta en CI, no en producción.
"""

from __future__ import annotations

from typing import Any

# capability → (tool/módulo real, kind de evidencia que produce, nivel LLM)
# nivel LLM: cuánto depende del juicio de un modelo (0=nada, 1=propone pero la
# evidencia es mecánica, 2=el juicio del LLM ES el producto — y por eso jamás
# puede ser evidencia). Las capas bajas deben tender a 0.
CAPABILITIES: dict[str, dict[str, Any]] = {
    "hypothesis_formulation": {"tool": "questions.question_engine",
                               "evidence_kind": "candidate", "llm_level": 2},
    "method_selection": {"tool": "science.method_catalog",
                         "evidence_kind": None, "llm_level": 1},
    "novelty_search": {"tool": "discovery.novelty_check",
                       "evidence_kind": "literature", "llm_level": 1},
    "data_resolution": {"tool": "portal.data_resolver",
                        "evidence_kind": None, "llm_level": 0},
    "experiment_design": {"tool": "portal.experiment_factory",
                          "evidence_kind": "experiment", "llm_level": 1},
    "anomaly_harvest": {"tool": "portal.anomalies",
                        "evidence_kind": "candidate", "llm_level": 1},
    "script_memory": {"tool": "science.math_probe._FileScriptCache",
                      "evidence_kind": None, "llm_level": 0},
    "counterexample_search": {"tool": "science.math_probe",
                              "evidence_kind": "experiment", "llm_level": 1},
    "symbolic_proof": {"tool": "science.formal_verify",
                       "evidence_kind": "lemma", "llm_level": 0},
    "smt_verification": {"tool": "science.proof_assistant",
                         "evidence_kind": "lemma", "llm_level": 0},
    "experiment_construction": {"tool": "science.turing",
                                "evidence_kind": "build", "llm_level": 1},
    "adversarial_critique": {"tool": "portal.critic",
                             "evidence_kind": "critique", "llm_level": 2},
    "internal_refereeing": {"tool": "science.noether",
                            "evidence_kind": "review", "llm_level": 2},
    "pattern_discovery": {"tool": "science.patterns",
                          "evidence_kind": "pattern", "llm_level": 0},
    "lateral_ideation": {"tool": "science.spark",
                         "evidence_kind": "spark", "llm_level": 2},
    "result_interpretation": {"tool": "science.research_loop.HumanAttitude",
                              "evidence_kind": "reformulation", "llm_level": 2},
    "orchestration": {"tool": "science.bohr + science.policy",
                      "evidence_kind": "decision", "llm_level": 1},
    "dossier_packaging": {"tool": "publication.dossier",
                          "evidence_kind": "dossier", "llm_level": 1},
}

# persona → capacidades (la interfaz humana mapeada a la arquitectura real)
PERSONA_CAPABILITIES: dict[str, list[str]] = {
    "hilbert": ["hypothesis_formulation"],
    "euler": ["method_selection"],
    "hipatia": ["novelty_search"],
    "arquimedes": ["data_resolution"],
    "davinci": ["experiment_design"],
    "kepler": ["anomaly_harvest"],
    "tycho": ["script_memory"],
    "popper": ["counterexample_search"],
    "euclides": ["symbolic_proof"],
    "godel": ["smt_verification"],
    "turing": ["experiment_construction"],
    "aristoteles": ["adversarial_critique"],
    "noether": ["internal_refereeing"],
    "mendeleev": ["pattern_discovery"],
    "ramanujan": ["lateral_ideation"],
    "feynman": ["result_interpretation"],
    "bohr": ["orchestration"],
    "gauss": ["dossier_packaging"],
}


def capability_of(persona: str) -> list[dict[str, Any]]:
    """Las capacidades reales (con herramienta y nivel LLM) detrás de una persona."""
    return [{"capability": c, **CAPABILITIES[c]}
            for c in PERSONA_CAPABILITIES.get(persona, [])
            if c in CAPABILITIES]


def validate_registry() -> list[str]:
    """Invariantes de la capa (los tests las corren): sin huérfanas ni fantasmas."""
    errors = []
    used = {c for caps in PERSONA_CAPABILITIES.values() for c in caps}
    for c in used - set(CAPABILITIES):
        errors.append(f"capacidad '{c}' asignada pero no definida")
    for c in set(CAPABILITIES) - used:
        errors.append(f"capacidad '{c}' definida pero sin persona responsable")
    return errors
