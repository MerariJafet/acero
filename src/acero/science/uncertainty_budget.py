"""Uncertainty budget — decompose uncertainty instead of hiding it in one number.

The reviewer: "A single aggregate confidence is not enough." A dossier should carry a
BUDGET: measurement + sampling + model + preprocessing + selection + missing-data +
generalization + causal + novelty uncertainty. The point is not one score but the
BREAKDOWN — so a reader sees which source dominates and where the result is fragile.

Each dimension is in [0,1] (0 = negligible, 1 = maximal). The combined figure is an
honest FLOOR ("at least this uncertain"), never a substitute for the breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

_DIMS = ("measurement", "sampling", "model", "preprocessing", "selection",
         "missing_data", "generalization", "causal", "novelty")

_LABELS = {
    "measurement": "medición", "sampling": "muestreo", "model": "modelo",
    "preprocessing": "preprocesamiento", "selection": "selección",
    "missing_data": "datos faltantes", "generalization": "generalización",
    "causal": "causal", "novelty": "novedad",
}


@dataclass
class UncertaintyBudget:
    measurement: float = 0.0
    sampling: float = 0.0
    model: float = 0.0
    preprocessing: float = 0.0
    selection: float = 0.0
    missing_data: float = 0.0
    generalization: float = 0.0
    causal: float = 0.0
    novelty: float = 0.0

    def _vals(self) -> dict[str, float]:
        return {f.name: max(0.0, min(1.0, float(getattr(self, f.name))))
                for f in fields(self)}

    def combined(self) -> float:
        """Floor on total uncertainty if sources were independent: 1 - Π(1 - u_i)."""
        prod = 1.0
        for v in self._vals().values():
            prod *= (1.0 - v)
        return 1.0 - prod

    def dominant(self) -> tuple[str, float]:
        vals = self._vals()
        name = max(vals, key=lambda k: vals[k])
        return name, vals[name]

    def report(self) -> dict[str, object]:
        vals = self._vals()
        dom, domv = self.dominant()
        return {
            "breakdown": {_LABELS[k]: round(vals[k], 3) for k in _DIMS},
            "combined_floor": round(self.combined(), 3),
            "dominant_source": _LABELS[dom],
            "dominant_value": round(domv, 3),
            "note": "el desglose es el resultado; 'combined_floor' es un piso, no una "
                    "confianza agregada",
        }

    def high_sources(self, threshold: float = 0.5) -> list[str]:
        """Dimensions whose uncertainty is high enough to threaten the claim."""
        return [_LABELS[k] for k, v in self._vals().items() if v >= threshold]
