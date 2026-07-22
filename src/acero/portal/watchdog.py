"""Scientific watchdog — PUSH monitoring of the literature.

Until now everything was pull: ACERO only searched when you clicked. The
watchdog turns it around: on a schedule (default daily) it re-runs each ACTIVE
hypothesis' English search query against OpenAlex/arXiv/Crossref, diffs the
results against what the project already indexed, and for every genuinely NEW
paper:

  * indexes it (kind="literature", flagged new_evidence=True, with abstract),
  * marks the hypothesis so the UI shows "📡 N papers nuevos", and
  * asks El Revisor for a mini-verdict: does this paper strengthen, weaken or
    kill the hypothesis? (task="nueva_evidencia", rendered like any critique).

Honesty: the watchdog only reports what the real APIs return — an empty diff
means "nothing new found by these sources", not "nothing new exists".
"""

from __future__ import annotations

import os
import threading
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

DEFAULT_INTERVAL_HOURS = 24.0


def _keys(papers: list[dict[str, Any]]) -> set[str]:
    out = set()
    for p in papers:
        doi = (p.get("doi") or "").lower().strip()
        if doi:
            out.add(f"doi:{doi}")
        t = (p.get("title") or "").lower().strip()[:60]
        if t:
            out.add(f"t:{t}")
    return out


class Watchdog:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    def scan_project(self, project_id: str, *, searcher: Any | None = None,
                     use_ai: bool = True, rows: int = 6) -> dict[str, Any]:
        """Diff each approved hypothesis' query against the live indexes."""
        from .hypothesis_flow import HypothesisFlow
        if searcher is None:
            from ..knowledge_mesh import mesh
            searcher = mesh.topical_search
        p = self.ledger.get_project(project_id)
        if p is None:
            return {"ok": False, "error": "project not found"}
        known = _keys(self.store.list_objects(project_id, kind="literature"))
        fl = HypothesisFlow(self._sf)
        by_hyp: list[dict[str, Any]] = []
        total_new = 0
        for h in fl.approved(project_id):
            query = ((h.get("confrontation") or {}).get("query_used") or "").strip()
            if not query:
                continue                      # not investigated yet → nothing to watch
            try:
                found = searcher(query, domain=p.domain or "", rows=rows)
            except Exception as exc:  # noqa: BLE001 - one bad query must not stop the scan
                by_hyp.append({"tag": h.get("tag"), "error": str(exc)[:120]})
                continue
            fresh = [f for f in found if not (_keys([f]) & known)]
            for f in fresh:
                lid = new_id("lit")
                rec = {"id": lid, "hyp_id": h["id"], "angle": h.get("tag", ""),
                       "title": f.get("title", ""), "doi": f.get("doi", ""),
                       "type": f.get("type", ""), "integrity": f.get("integrity", ""),
                       "url": f.get("url", ""), "authors": f.get("authors", []),
                       "abstract": f.get("abstract", ""),
                       "source": f.get("source", ""),
                       "relevance": f.get("relevance"),
                       "new_evidence": True, "discovered_at": now_iso(),
                       "query_used": query}
                self.store.put(project_id, "literature", lid, rec, status="INDEXED",
                               actor="watchdog",
                               summary=f"📡 paper nuevo para {h.get('tag')}: "
                                       f"{(f.get('title') or '')[:50]}")
                known |= _keys([f])
            if fresh:
                total_new += len(fresh)
                self.store.update_payload(h["id"], {
                    "new_evidence_count": int(h.get("new_evidence_count") or 0)
                    + len(fresh),
                    "new_evidence_at": now_iso()})
                if use_ai:
                    from .critic import critique_async
                    plist = "\n".join(
                        f"- «{f.get('title','')}»: {(f.get('abstract') or '')[:250]}"
                        for f in fresh[:4])
                    critique_async(
                        project_id, h["id"], "nueva_evidencia",
                        f"Salió LITERATURA NUEVA para la hipótesis "
                        f"«{h.get('title','')}»:\n{plist}\n\n¿Estos papers la "
                        "FORTALECEN, la DEBILITAN o la MATAN? Sé específico por paper.",
                        self._sf)
            by_hyp.append({"tag": h.get("tag"), "query": query[:80],
                           "checked": len(found), "new": len(fresh),
                           "new_titles": [f.get("title", "")[:70] for f in fresh[:4]]})
        sid = new_id("wsc")
        scan = {"id": sid, "at": now_iso(), "total_new": total_new, "by_hyp": by_hyp}
        self.store.put(project_id, "watch_scan", sid, scan, status="DONE",
                       actor="watchdog",
                       summary=f"📡 vigilancia: {total_new} papers nuevos")
        return {"ok": True, **scan}

    def last_scan(self, project_id: str) -> dict[str, Any] | None:
        scans = self.store.list_objects(project_id, kind="watch_scan")
        return max(scans, key=lambda s: s.get("at") or "", default=None)

    def scan_all(self, **kw: Any) -> dict[str, Any]:
        out = []
        for p in self.ledger.list_projects():
            r = self.scan_project(p.id, **kw)
            if r.get("ok"):
                out.append({"project": p.title[:40], "new": r["total_new"]})
        return {"ok": True, "projects": out}


def watchdog_on_startup() -> None:
    """Portal boot hook: scan periodically in the background (default daily)."""
    if os.environ.get("ACERO_WATCHDOG_DISABLED") == "1":
        return
    hours = float(os.environ.get("ACERO_WATCHDOG_HOURS", DEFAULT_INTERVAL_HOURS))

    def _loop() -> None:
        import time
        time.sleep(120)                       # let the portal settle first
        while True:
            try:
                wd = Watchdog()
                stale = True
                for p in wd.ledger.list_projects():
                    last = wd.last_scan(p.id)
                    if last and (now_iso()[:10] == (last.get("at") or "")[:10]):
                        stale = False         # already scanned today
                if stale:
                    wd.scan_all()
            except Exception:  # noqa: BLE001 - the watchdog must never crash the portal
                pass
            time.sleep(max(3600.0, hours * 3600.0))
    threading.Thread(target=_loop, name="watchdog", daemon=True).start()
