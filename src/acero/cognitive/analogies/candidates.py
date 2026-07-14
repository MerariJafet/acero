"""Codex-backed analogy candidate proposal (Sprint 8.6).

Codex may PROPOSE a mapping between two systems; ACERO does not accept it — the
structural/dimensional/predictive validation decides. Every proposal records its
provenance (provider, model, tokens). A deterministic mock lets the flow run offline.
"""

from __future__ import annotations

from typing import Any

_PAIR = {
    "type": "object",
    "properties": {"from": {"type": "string"}, "to": {"type": "string"}},
    "required": ["from", "to"], "additionalProperties": False,
}
# Codex --output-schema (OpenAI structured outputs) requires every property in
# 'required' and does NOT support open-ended object maps; use arrays of pairs.
CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "entity_mapping": {"type": "array", "items": _PAIR},
        "relation_mapping": {"type": "array", "items": _PAIR},
        "shared_structure": {"type": "array", "items": {"type": "string"}},
        "differences": {"type": "array", "items": {"type": "string"}},
        "transfer_predictions": {"type": "array", "items": {"type": "string"}},
        "possible_failures": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["entity_mapping", "relation_mapping", "shared_structure", "differences",
                 "transfer_predictions", "possible_failures"],
    "additionalProperties": False,
}


def _pairs_to_map(pairs: Any) -> dict[str, str]:
    if isinstance(pairs, dict):
        return {str(k): str(v) for k, v in pairs.items()}
    out: dict[str, str] = {}
    for p in pairs or []:
        if isinstance(p, dict) and "from" in p and "to" in p:
            out[str(p["from"])] = str(p["to"])
    return out

_PROMPT = """You are proposing a SCIENTIFIC analogy candidate between two systems. Give a
structural mapping (entities and relations), the shared structure, the physical
DIFFERENCES, predictions that could transfer, and possible failure modes. Do NOT
claim the analogy is valid — it will be tested. Return JSON only.

Source system: {source}
Target system: {target}"""


def propose_candidate(provider: Any, source: str, target: str) -> dict[str, Any]:
    if not hasattr(provider, "complete_json"):
        raise TypeError("analogy candidate proposal requires a provider with complete_json")
    prompt = _PROMPT.format(source=source, target=target)
    result = provider.complete_json(prompt, CANDIDATE_SCHEMA)
    result["entity_mapping"] = _pairs_to_map(result.get("entity_mapping"))
    result["relation_mapping"] = _pairs_to_map(result.get("relation_mapping"))
    result["_provenance"] = {
        "provider": getattr(provider, "name", "unknown"),
        "model": getattr(provider, "model", None) or "codex-default",
        "token_usage": getattr(provider, "last_usage", {}) or {},
    }
    return result


class MockAnalogyProposer:
    name = "mock"

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0) -> dict:
        return {"entity_mapping": {"mass": "inductance", "damping": "resistance"},
                "relation_mapping": {"restoring_force": "voltage_across_capacitor"},
                "shared_structure": ["second-order linear ODE"],
                "differences": ["mechanical vs electrical variables"],
                "transfer_predictions": ["resonance frequency"],
                "possible_failures": ["nonlinear regime", "radiation losses"]}
