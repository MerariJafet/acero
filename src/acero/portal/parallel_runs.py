"""Parallel research runs — one SUBAGENT (worker thread + its own Codex process)
per hypothesis/experiment, with live per-item progress.

"Correr todas" used to run sequentially inside one HTTP request (minutes of
blocking). Now a run starts in the background: each item gets a worker that owns
its own DB session and shells its own `codex exec` subprocess (a real local
subagent — still no paid API). Progress is polled via /runs/{run_id}.

Concurrency safety: SQLite is in WAL mode with busy_timeout=30s (ledger/db.py),
and each worker uses its own session from the factory. Workers are capped so we
never stampede the machine with Codex processes.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id

# Cap of concurrent Codex subagents (each is a full local model process).
MAX_SUBAGENTS = 3

_LOCK = threading.Lock()
_RUNS: dict[str, dict[str, Any]] = {}          # in-memory registry (this process)


def _registry_put(run: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS[run["id"]] = run
        # keep the registry bounded (old finished runs age out)
        if len(_RUNS) > 50:
            done = [k for k, r in _RUNS.items() if r["status"] != "RUNNING"]
            for k in done[:-10]:
                _RUNS.pop(k, None)


def get_run(run_id: str) -> dict[str, Any] | None:
    with _LOCK:
        r = _RUNS.get(run_id)
        return dict(r, items=[dict(i) for i in r["items"]]) if r else None


def _mark(run: dict[str, Any], idx: int, **fields: Any) -> None:
    with _LOCK:
        run["items"][idx].update(fields)
        done = sum(1 for i in run["items"] if i["status"] in ("DONE", "ERROR"))
        run["done"] = done
        if done == run["total"]:
            run["status"] = "DONE"
            run["finished_at"] = now_iso()


def start_run(kind: str, items: list[dict[str, Any]],
              work: Callable[[dict[str, Any]], dict[str, Any]],
              *, max_workers: int = MAX_SUBAGENTS) -> dict[str, Any]:
    """Launch a background run: `work(item)` per item, MAX_SUBAGENTS at a time.

    Each item dict needs `id` and `label`; `work` must be thread-safe (it should
    build its own flow/session per call). Returns the run snapshot immediately.
    """
    run: dict[str, Any] = {
        "id": new_id("run"), "kind": kind, "status": "RUNNING",
        "total": len(items), "done": 0, "started_at": now_iso(),
        "finished_at": None,
        "items": [{"id": it["id"], "label": it.get("label", ""),
                   "status": "PENDING", "summary": ""} for it in items],
    }
    _registry_put(run)
    if not items:
        run["status"] = "DONE"
        run["finished_at"] = now_iso()
        return get_run(run["id"]) or run

    def _worker(idx: int, item: dict[str, Any]) -> None:
        _mark(run, idx, status="RUNNING")
        try:
            out = work(item)
            _mark(run, idx, status="DONE",
                  summary=str(out.get("summary", ""))[:160])
        except Exception as exc:  # noqa: BLE001 - a failed subagent must not kill the run
            _mark(run, idx, status="ERROR", summary=str(exc)[:160])

    def _launch() -> None:
        with ThreadPoolExecutor(max_workers=max(1, max_workers),
                                thread_name_prefix=f"subagent-{kind}") as pool:
            for idx, item in enumerate(items):
                pool.submit(_worker, idx, item)

    threading.Thread(target=_launch, name=f"run-{run['id']}", daemon=True).start()
    return get_run(run["id"]) or run


# --- concrete runs ----------------------------------------------------------

def start_investigate_all(project_id: str, *, use_ai: bool = True,
                          session_factory: Any | None = None,
                          max_workers: int = MAX_SUBAGENTS) -> dict[str, Any]:
    """One literature subagent per APPROVED hypothesis, in parallel."""
    from .hypothesis_flow import HypothesisFlow
    sf = session_factory
    approved = HypothesisFlow(sf).approved(project_id)
    items = [{"id": h["id"], "label": f"{h.get('tag','')}: {h.get('title','')[:60]}"}
             for h in approved]

    def work(item: dict[str, Any]) -> dict[str, Any]:
        fl = HypothesisFlow(sf)                    # own session per subagent
        r = fl.investigate(project_id, item["id"], use_ai=use_ai)
        if not r.get("ok"):
            raise RuntimeError(r.get("error", "investigate failed"))
        stance = (r.get("confrontation") or {}).get("stance", "")
        return {"summary": f"{r.get('n_papers', 0)} papers · {stance}"}

    return start_run("investigate_all", items, work, max_workers=max_workers)


def start_run_all_experiments(project_id: str, *, use_ai: bool = True,
                              session_factory: Any | None = None,
                              max_workers: int = MAX_SUBAGENTS) -> dict[str, Any]:
    """One subagent per PROPOSED experiment, in parallel."""
    from .hypothesis_flow import HypothesisFlow
    sf = session_factory
    fl0 = HypothesisFlow(sf)
    proposed = [e for e in fl0.store.list_objects(project_id, kind="experiment")
                if (e.get("status") or "") == "PROPOSED"]
    items = [{"id": e["id"],
              "label": f"{e.get('hyp_tag','')}: {e.get('title','')[:60]}"}
             for e in proposed]

    def work(item: dict[str, Any]) -> dict[str, Any]:
        fl = HypothesisFlow(sf)
        r = fl.run_experiment(project_id, item["id"], use_ai=use_ai)
        if not r.get("ok"):
            raise RuntimeError(r.get("error", "experiment failed"))
        return {"summary": "análisis real" if r.get("mode") == "real_analysis"
                else "plan reproducible (pendiente de datos)"}

    return start_run("run_all_experiments", items, work, max_workers=max_workers)
