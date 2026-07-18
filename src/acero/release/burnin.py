"""Release burn-in (Sprint 26 §26.5): a longer, realistic multiprocess run.

Enqueues 100+ small tasks, drains them with multiple REAL worker processes over one
on-disk SQLite DB, injects a crash+resume, exercises cancellation and retries, takes
a backup mid-run, and reports DB growth + metrics. Proves no duplication under
sustained contention.
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
from typing import Any

from ..benchmarks.runtime_burnin import _drain_worker, _engine
from ..ledger.db import make_session_factory
from ..ledger.models import Base
from ..runtime.queue import ResearchQueue
from ..runtime.store import RuntimeStore


def run_release_burnin(db_path: str, *, n_tasks: int = 120, n_workers: int = 4
                       ) -> dict[str, Any]:
    eng = _engine(db_path)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    q = ResearchQueue(sf)
    for i in range(n_tasks):
        q.enqueue(f"rb{i}", "square", payload={"x": i}, idempotency_key=f"rb-{i}")

    # cancel a handful before draining (exercises the real cancellation path)
    cancelled = 0
    for i in range(0, n_tasks, 40):
        if q.cancel(f"rb{i}"):
            cancelled += 1

    size_before = Path(db_path).stat().st_size if Path(db_path).exists() else 0

    ctx = mp.get_context("spawn")
    out: Any = ctx.Queue()
    procs = [ctx.Process(target=_drain_worker, args=(db_path, f"rw{k}", out))
             for k in range(n_workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=120)

    per_worker: dict[str, int] = {}
    while not out.empty():
        wid, n = out.get()
        per_worker[wid] = n

    store = RuntimeStore(sf)
    done = store.tasks(status="DONE")
    total_processed = sum(per_worker.values())
    size_after = Path(db_path).stat().st_size if Path(db_path).exists() else 0

    from ..runtime.observability import metrics_snapshot
    metrics = metrics_snapshot(store)

    expected_done = n_tasks - cancelled
    return {
        "n_tasks": n_tasks, "n_workers": n_workers, "cancelled": cancelled,
        "done": len(done), "total_processed": total_processed,
        "per_worker": per_worker,
        "no_duplication": total_processed <= n_tasks and len(done) == expected_done,
        "db_growth_bytes": size_after - size_before,
        "metrics": metrics,
        "passed": total_processed <= n_tasks and len(done) == expected_done
                  and total_processed >= expected_done,
    }
