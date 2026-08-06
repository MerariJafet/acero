"""Mass parallel sweep — generative breadth with ACERO's gates.

The AI math episode that actually produced value did it by FAN-OUT: thousands of
attempts in parallel, then automatic filtering. ACERO's PI loop was one-at-a-time.
This adds the breadth: generate K candidate hypotheses at once, then filter them
CONCURRENTLY through two cheap gates before spending any experiment compute:

  1. Novelty (anti-Erdősgate): skip anything literature already resolved.
  2. EVA (epistemic gate): drop vague / HARKing / trivial / confirm-only claims.

Survivors are ranked by (novelty headroom × EVA pass) and returned — the caller (or
the PI) enqueues them. So we get GPT-5-style generative power, but every candidate
passes the same honesty gates before compute, and nothing is called a discovery.

Generator, novelty checker and EVA gate are all injectable for offline tests; the
fan-out uses a bounded thread pool (same cap as missions).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

MAX_WORKERS = max(1, min(16, int(os.environ.get("ACERO_SWEEP_WORKERS", "6"))))


def _score(novelty: dict[str, Any], eva: dict[str, Any]) -> float:
    """Higher = more worth running: EVA-clean AND unlikely to be a known result."""
    if not eva.get("proceed"):
        return 0.0
    headroom = 1.0 - float(novelty.get("recovery_risk", 0.5))   # far from 'already known'
    if novelty.get("verdict") == "already_resolved":
        return 0.0
    return round(0.2 + 0.8 * headroom, 4)


class SweepEngine:
    def __init__(self, sf: Any = None, *, generator: Any = None,
                 novelty: Any = None, eva: Any = None) -> None:
        self._sf = sf
        self._generator = generator
        self._novelty = novelty
        self._eva = eva

    # --- injectable defaults --------------------------------------------------
    def _generate(self, pid: str, n: int, focus: str) -> list[dict[str, Any]]:
        if self._generator is not None:
            return self._generator(pid, n, focus)
        from .hypotheses import HypothesisService
        g = HypothesisService(self._sf).generate(pid, n=n, use_ai=True, focus=focus)
        return g.get("created", []) if isinstance(g, dict) else []

    def _check_novelty(self, hyp: dict[str, Any]) -> dict[str, Any]:
        if self._novelty is not None:
            return self._novelty(hyp)
        from ..discovery.novelty_check import NoveltyChecker
        claim = str(hyp.get("title") or hyp.get("trigger_question") or "")
        return NoveltyChecker().check(claim)

    def _check_eva(self, hyp: dict[str, Any]) -> dict[str, Any]:
        if self._eva is not None:
            return self._eva(hyp)
        from .epistemic_bridge import internal_eva
        return internal_eva(hyp, use_ai=True)

    def _evaluate(self, hyp: dict[str, Any]) -> dict[str, Any]:
        """The per-candidate work that runs in parallel: novelty + EVA + score."""
        novelty = self._check_novelty(hyp)
        eva = self._check_eva(hyp)
        return {"hyp": hyp, "novelty": novelty, "eva": eva,
                "score": _score(novelty, eva)}

    def run(self, pid: str, *, n: int = 8, focus: str = "") -> dict[str, Any]:
        """Generate n candidates, filter them concurrently, rank survivors."""
        cands = self._generate(pid, n, focus)
        results: list[dict[str, Any]] = []
        if cands:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS,
                                    thread_name_prefix="sweep") as pool:
                futs = [pool.submit(self._evaluate, h) for h in cands]
                for f in as_completed(futs):
                    try:
                        results.append(f.result())
                    except Exception:  # noqa: BLE001 - one bad candidate never kills the sweep
                        continue
        survivors = sorted((r for r in results if r["score"] > 0),
                           key=lambda r: -r["score"])
        rejected = [r for r in results if r["score"] <= 0]
        return {
            "generated": len(cands),
            "evaluated": len(results),
            "survivors": [{
                "id": r["hyp"].get("id"),
                "title": (r["hyp"].get("title") or "")[:120],
                "score": r["score"],
                "novelty": r["novelty"].get("verdict"),
                "recovery_risk": r["novelty"].get("recovery_risk"),
            } for r in survivors],
            "rejected": [{
                "title": (r["hyp"].get("title") or "")[:120],
                "reason": ("ya resuelto en literatura"
                           if r["novelty"].get("verdict") == "already_resolved"
                           else "; ".join(r["eva"].get("blockers", []) or ["descartada"])),
            } for r in rejected],
            "kept": len(survivors),
            "_survivors_full": survivors,      # for callers that enqueue (not serialized to UI)
        }

    def run_and_enqueue(self, pid: str, *, n: int = 8, focus: str = "") -> dict[str, Any]:
        """Sweep, then approve + start missions for the survivors (PI-style)."""
        out = self.run(pid, n=n, focus=focus)
        from .hypothesis_flow import HypothesisFlow
        from .missions import MissionEngine
        flow = HypothesisFlow(self._sf)
        approved = 0
        for r in out["_survivors_full"]:
            hid = r["hyp"].get("id")
            if hid:
                try:
                    flow.set_status(pid, hid, "APPROVED", "sweep")
                    approved += 1
                except Exception:  # noqa: BLE001
                    continue
        started = 0
        if approved:
            res = MissionEngine(self._sf).start_all(pid, use_ai=True, sync=False)
            started = len(res.get("started", [])) if isinstance(res, dict) else 0
        out.pop("_survivors_full", None)
        out["approved"] = approved
        out["missions_started"] = started
        return out
