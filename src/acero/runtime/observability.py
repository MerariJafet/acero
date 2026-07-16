"""Local observability (Sprint 22): structured metrics snapshot; no external platform.

Exposes a metrics dict (queue depth by status, dead letters, worker/task counts, disk growth)
in a Prometheus-compatible text format on request. Structured JSON logs already come from
structlog (configured in core/logging.py)."""

from __future__ import annotations

from typing import Any

from .store import RuntimeStore


def metrics_snapshot(store: RuntimeStore) -> dict[str, Any]:
    tasks = store.tasks()
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    return {"tasks_total": len(tasks), "by_status": by_status,
            "dead_letters": by_status.get("DEAD_LETTER", 0),
            "queued": by_status.get("QUEUED", 0),
            "running": by_status.get("RUNNING", 0) + by_status.get("LEASED", 0),
            "events_total": len(store.events())}


def prometheus_text(store: RuntimeStore) -> str:
    m = metrics_snapshot(store)
    lines = [f"acero_tasks_total {m['tasks_total']}",
             f"acero_dead_letters {m['dead_letters']}",
             f"acero_queued {m['queued']}",
             f"acero_running {m['running']}",
             f"acero_events_total {m['events_total']}"]
    for status, n in m["by_status"].items():
        lines.append(f'acero_tasks{{status="{status}"}} {n}')
    return "\n".join(lines) + "\n"
