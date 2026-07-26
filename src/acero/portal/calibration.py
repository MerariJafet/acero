"""Self-calibration memory — the program remembers how each DOMAIN was tuned and
auto-adjusts within SAFE bounds after every recovery-benchmark run.

Design principles (so auto-improvement HELPS but never BREAKS the system):
  1. It tunes PARAMETERS (data), never code. Code changes stay human.
  2. A CONSTITUTION FLOOR is inviolable: specificity on null controls must stay perfect
     (zero false positives). ACERO's whole value is "no te engaña" — no adjustment may
     trade that away. A calibration that produces a false positive is ROLLED BACK.
  3. One knob, one bounded step at a time; every decision logged with a rationale
     (the "retro"); every change reversible (last-safe snapshot kept).
  4. Per-DOMAIN memory: astronomy may need a different tolerance than genomics. What is
     learned in one field is remembered and does not leak into another.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root

# Tunable knobs, their safe bounds, and defaults. Only these may be auto-adjusted.
DEFAULTS: dict[str, Any] = {
    "cross_check_rel_tol": 0.15,       # ↑ = more sensitive, ↓ = more specific
    "simplicity_emphasis": True,       # prefer the simplest sufficient test
}
BOUNDS: dict[str, tuple[float, float]] = {
    "cross_check_rel_tol": (0.05, 0.30),
}
STEP: dict[str, float] = {"cross_check_rel_tol": 0.03}

# INVIOLABLE: fraction of null controls that must stay correctly non-positive.
SPECIFICITY_FLOOR = 1.0


def _calib_path() -> Path:
    import os
    env = os.environ.get("ACERO_CALIBRATION_PATH", "").strip()
    return Path(env) if env else repo_root() / "research" / "calibration.json"


class Calibration:
    """Persistent per-domain knobs + benchmark history + auto-tune decisions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _calib_path()
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - missing/corrupt ⇒ fresh
            return {"domains": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def _dom(self, domain: str) -> dict[str, Any]:
        d = self._data.setdefault("domains", {}).setdefault(
            domain or "general",
            {"knobs": dict(DEFAULTS), "history": [], "decisions": [],
             "last_safe": dict(DEFAULTS)})
        # backfill any new knob defaults without clobbering learned values
        for k, v in DEFAULTS.items():
            d["knobs"].setdefault(k, v)
        return d

    def get(self, domain: str) -> dict[str, Any]:
        """The active knobs for a domain (used by the pipeline)."""
        return dict(self._dom(domain)["knobs"])

    def record_benchmark(self, domain: str, summary: dict[str, Any]) -> None:
        """Append a recovery-benchmark result to the domain's retro history.

        `summary` should carry: positives_correct, positives_total, nulls_correct,
        nulls_total, false_positives, accuracy.
        """
        d = self._dom(domain)
        d["history"].append({"at": now_iso(), "knobs": dict(d["knobs"]), **summary})
        self._save()

    def _clamp(self, knob: str, value: float) -> float:
        lo, hi = BOUNDS[knob]
        return max(lo, min(hi, round(value, 4)))

    def auto_tune(self, domain: str) -> dict[str, Any]:
        """Decide ONE safe adjustment from the latest benchmark, respecting the floor.

        - false positives on nulls  → ROLLBACK to last-safe (specificity is sacred).
        - specificity perfect but sensitivity < 1 and room to loosen → nudge tolerance up.
        - already perfect / no room → no change.
        Returns the decision (also appended to the retro).
        """
        d = self._dom(domain)
        if not d["history"]:
            return {"action": "none", "reason": "sin historial todavía"}
        last = d["history"][-1]
        # validity floor: never learn from a run whose data pipeline failed
        if last.get("valid") is False:
            dec = {"at": now_iso(), "domain": domain or "general",
                   "action": "skip_invalid", "knob": "cross_check_rel_tol",
                   "before": d["knobs"]["cross_check_rel_tol"],
                   "after": d["knobs"]["cross_check_rel_tol"],
                   "reason": "corrida inválida (pipeline sin evidencia): no se ajusta"}
            d["decisions"].append(dec)
            self._save()
            return dec
        nulls_t = last.get("nulls_total", 0) or 0
        fp = last.get("false_positives", 0) or 0
        pos_t = last.get("positives_total", 0) or 0
        pos_c = last.get("positives_correct", 0) or 0
        specificity = 1.0 if nulls_t == 0 else (nulls_t - fp) / nulls_t
        knob = "cross_check_rel_tol"
        before = d["knobs"][knob]

        if specificity < SPECIFICITY_FLOOR:
            # UNSAFE: a null came back positive. Revert toward stricter + snapshot floor.
            after = self._clamp(knob, min(d["last_safe"].get(knob, before),
                                          before - STEP[knob]))
            action, reason = "rollback", (
                f"especificidad {specificity:.2f} < piso {SPECIFICITY_FLOOR}: "
                f"{fp} falso(s) positivo(s) en nulos → tolerancia {before}→{after} "
                "(la especificidad es inviolable)")
        elif pos_t and pos_c < pos_t and before < BOUNDS[knob][1]:
            # SAFE to gain sensitivity: specificity perfect, positives still missed.
            after = self._clamp(knob, before + STEP[knob])
            d["last_safe"][knob] = before      # this value is proven safe
            action, reason = "loosen", (
                f"especificidad perfecta pero sensibilidad {pos_c}/{pos_t}: "
                f"subo tolerancia {before}→{after} para recuperar más positivos")
        else:
            d["last_safe"][knob] = before
            action, reason = "none", (
                "sensibilidad y especificidad OK, o sin margen de ajuste seguro"
                if pos_c >= pos_t else "sin margen (tolerancia en su cota)")
            after = before

        if after != before:
            d["knobs"][knob] = after
        decision = {"at": now_iso(), "domain": domain or "general", "action": action,
                    "knob": knob, "before": before, "after": after, "reason": reason,
                    "specificity": round(specificity, 3),
                    "sensitivity": round(pos_c / pos_t, 3) if pos_t else None}
        d["decisions"].append(decision)
        self._save()
        return decision

    def retro(self, domain: str | None = None) -> dict[str, Any]:
        """The learning memory: knobs + last decisions per domain (for humans/cron)."""
        if domain:
            d = self._dom(domain)
            return {"domain": domain, "knobs": d["knobs"],
                    "decisions": d["decisions"][-8:], "runs": len(d["history"])}
        return {dom: {"knobs": v["knobs"], "runs": len(v["history"]),
                      "last_decision": (v["decisions"] or [{}])[-1]}
                for dom, v in self._data.get("domains", {}).items()}
