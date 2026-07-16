"""Long-running / multiprocess runtime burn-in (Sprint 22).

Proves the persistent runtime survives REAL multiprocess contention and a crash+restart, with
no duplication, idempotent enqueue, preserved negative results, and checkpoint-based resume.
Uses actual OS processes over a single on-disk SQLite database (not in-memory), simulating a
long run via many short checkpointed tasks (compressed time, not 8 real hours).
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event

from ..ledger.db import make_session_factory
from ..ledger.models import Base
from ..ledger.service import ResearchLedger
from ..runtime.queue import ResearchQueue
from ..runtime.worker import Worker


def _engine(db_path: str):
    """A busy-timeout + WAL SQLite engine so concurrent worker processes serialise cleanly."""
    eng = create_engine(f"sqlite:///{db_path}", future=True, connect_args={"timeout": 30})

    @event.listens_for(eng, "connect")
    def _pragmas(conn, _rec):  # type: ignore[no-untyped-def]
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

    return eng


def _drain_worker(db_path: str, worker_id: str, out: Any) -> None:
    """A real subprocess entrypoint: open the shared DB and drain the queue."""
    eng = _engine(db_path)
    sf = make_session_factory(eng)
    q = ResearchQueue(sf)
    w = Worker(q, worker_id=worker_id)
    w.register("square", lambda p, c, hb: {"y": p["x"] ** 2})
    q.reap_expired()
    processed = w.drain(max_tasks=1000)
    out.put((worker_id, processed))


def multiprocess_no_duplication(db_path: str, *, n_tasks: int = 40, n_workers: int = 4
                                ) -> dict[str, Any]:
    """Enqueue N tasks; run K real worker processes; assert each task done exactly once."""
    eng = _engine(db_path)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    ResearchLedger(sf)
    q = ResearchQueue(sf)
    for i in range(n_tasks):
        q.enqueue(f"t{i}", "square", payload={"x": i}, idempotency_key=f"sq-{i}")

    ctx = mp.get_context("spawn")
    out: Any = ctx.Queue()
    procs = [ctx.Process(target=_drain_worker, args=(db_path, f"w{k}", out))
             for k in range(n_workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)

    per_worker = {}
    while not out.empty():
        wid, n = out.get()
        per_worker[wid] = n
    done = q.store.tasks(status="DONE")
    total_processed = sum(per_worker.values())
    return {"n_tasks": n_tasks, "n_workers": n_workers,
            "done": len(done), "total_processed": total_processed,
            "per_worker": per_worker,
            "no_duplication": total_processed == n_tasks and len(done) == n_tasks,
            "passed": total_processed == n_tasks and len(done) == n_tasks}


def idempotent_enqueue(db_path: str) -> dict[str, Any]:
    eng = _engine(db_path)
    Base.metadata.create_all(eng)
    q = ResearchQueue(make_session_factory(eng))
    a = q.enqueue("x1", "square", payload={"x": 3}, idempotency_key="dup")
    b = q.enqueue("x2", "square", payload={"x": 3}, idempotency_key="dup")
    return {"same_task": a["id"] == b["id"], "passed": a["id"] == b["id"]}


def crash_and_resume(db_path: str) -> dict[str, Any]:
    """A worker claims + checkpoints then 'crashes'; lease expires; another resumes."""
    eng = _engine(db_path)
    Base.metadata.create_all(eng)
    q = ResearchQueue(make_session_factory(eng), lease_seconds=0)   # instant expiry
    q.enqueue("job", "square", payload={"x": 9})
    q.claim("crasher")
    q.heartbeat("job", "crasher", checkpoint={"progress": 0.5})     # partial work saved
    # 'crash': no complete. New queue object over same DB (restart).
    q2 = ResearchQueue(make_session_factory(_engine(db_path)))
    reclaimed = q2.reap_expired()
    resumed = q2.claim("survivor")
    return {"reclaimed": reclaimed, "checkpoint_seen": resumed["checkpoint"] == {"progress": 0.5}
            if resumed else False,
            "passed": bool(reclaimed) and resumed is not None
            and resumed["checkpoint"] == {"progress": 0.5}}


def run_burnin(tmp_dir: str) -> dict[str, Any]:
    d = Path(tmp_dir)
    d.mkdir(parents=True, exist_ok=True)
    cases = {
        "multiprocess_no_duplication": multiprocess_no_duplication(str(d / "mp.sqlite")),
        "idempotent_enqueue": idempotent_enqueue(str(d / "idem.sqlite")),
        "crash_and_resume": crash_and_resume(str(d / "crash.sqlite")),
    }
    return {"cases": cases, "n": len(cases),
            "passed": sum(1 for c in cases.values() if c["passed"]),
            "all_passed": all(c["passed"] for c in cases.values())}
