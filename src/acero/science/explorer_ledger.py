"""ExplorerLedger — la memoria de "qué caminos funcionaron", que el PROGRAMA guarda.

Merari: "a veces solo sabrá que algo funciona cuando lo pruebe… guardar resultados".
Exacto. El Explorador prueba enfoques por ejecución (fuerza bruta computacional cuando
hace falta) y a veces la única forma de saber si una pieza encaja es correrla. Este
libro PERSISTE esos resultados: por objetivo guarda los enfoques viables, qué piezas de
LEGO usaron, la hipótesis y el veredicto. Así el programa:

  * RECUERDA: si el objetivo (o uno equivalente) ya se resolvió, reofrece los caminos
    que funcionaron como pistas al divergir — no re-deduce desde cero;
  * ACUMULA: cada corrida deja el programa un poco más capaz, en disco, auditable;
  * es HONESTO: guarda el veredicto tal cual (verified / holds_empirically / …); no
    convierte "funcionó empíricamente" en "probado".

Es dato en disco (JSON), no otra llamada al LLM. Store inyectable para tests offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-záéíóúñ0-9 ]+")


def _norm(goal: str) -> str:
    g = _PUNCT.sub(" ", goal.lower())
    return _WS.sub(" ", g).strip()


class ExplorerLedger:
    def __init__(self, store: Path | None = None) -> None:
        self._store = store
        self._path = (store / "results.json") if store else None
        self._mem: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path or not self._path.exists():
            return {}
        try:
            rows = json.loads(self._path.read_text(encoding="utf-8"))
            return {r["key"]: r for r in rows if "key" in r}
        except Exception:  # noqa: BLE001
            return {}

    def _flush(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(list(self._mem.values()), ensure_ascii=False, indent=2),
            encoding="utf-8")

    # --- write ----------------------------------------------------------------
    def record(self, goal: str, result: dict[str, Any]) -> None:
        """Store the outcome of an exploration. Overwrites a stronger verdict only."""
        key = _norm(goal)
        row = {
            "key": key, "goal": goal,
            "status": result.get("status"),
            "verdict": result.get("verdict"),
            "hypothesis": result.get("hypothesis"),
            "viable_approaches": result.get("viable_approaches") or [],
        }
        prev = self._mem.get(key)
        # keep the strongest verdict we have ever seen for this goal
        if prev and _rank(str(prev.get("verdict") or "")) > _rank(result.get("verdict")):
            return
        self._mem[key] = row
        self._flush()

    # --- read -----------------------------------------------------------------
    def recall(self, goal: str) -> dict[str, Any] | None:
        return self._mem.get(_norm(goal))

    def hints(self, goal: str) -> str:
        """Compact text of prior working approaches, for the diverge prompt."""
        r = self.recall(goal)
        if not r or not r.get("viable_approaches"):
            return ""
        lines = []
        for a in r["viable_approaches"][:6]:
            tools = ",".join(a.get("tools_used") or [])
            lines.append(f"- {a.get('method')} → {a.get('candidate')}"
                         + (f" [piezas: {tools}]" if tools else ""))
        return (f"ANTES YA FUNCIONARON estos caminos (veredicto {r.get('verdict')}); "
                "puedes reutilizarlos o mejorarlos:\n" + "\n".join(lines))

    def all(self) -> list[dict[str, Any]]:
        return list(self._mem.values())


def _rank(verdict: str | None) -> int:
    return {"verified": 4, "refuted": 4, "holds_empirically": 2,
            "candidate": 1, "inconclusive": 0}.get(verdict or "", 0)
