"""Obsidian vault exporter — structured research memory.

Mirrors a project's research flow into an Obsidian vault as linked markdown notes:
project MOC → hypotheses (with version history) → literature (real papers with
abstract/DOI/source) → experiments (result or reproducible plan). Everything is
regenerable from the ledger (the vault is a VIEW of ACERO's memory, not the source
of truth), so sync overwrites ACERO-managed notes; human notes elsewhere in the
vault are never touched.

Vault location: $ACERO_OBSIDIAN_VAULT, default ~/Documents/ACERO-Research — a
DEDICATED vault, kept separate from any personal/business vault on purpose.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any

from ..core.clock import now_iso

_BANNER = "> [!info] Nota generada por ACERO — se regenera en cada sync; no editar a mano.\n"
# parallel subagents may finish at the same time; serialize vault writes
_SYNC_LOCK = threading.Lock()


def vault_root() -> Path:
    env = os.environ.get("ACERO_OBSIDIAN_VAULT", "").strip()
    return Path(env) if env else Path.home() / "Documents" / "ACERO-Research"


def _safe(name: str, limit: int = 80) -> str:
    """Filesystem/Obsidian-safe note name."""
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", name or "")
    name = re.sub(r"\s+", " ", name).strip()
    return (name[:limit].strip() or "sin-titulo")


def _fm(d: dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in d.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"  - {x}" for x in v]
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


class ObsidianExporter:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or vault_root()

    # --- layout -------------------------------------------------------------
    def _ensure_vault(self) -> None:
        (self.root / ".obsidian").mkdir(parents=True, exist_ok=True)
        home = self.root / "Home.md"
        if not home.exists():
            home.write_text(
                "# 🔬 ACERO Research Vault\n\n"
                "Memoria estructurada de las investigaciones de ACERO. Cada proyecto tiene "
                "su carpeta con hipótesis, literatura real (DOI verificado) y experimentos.\n\n"
                "Regla epistémica: la síntesis del LLM es ayuda de razonamiento, **nunca "
                "evidencia**; nada aquí es un descubrimiento sin revisión humana.\n",
                encoding="utf-8")

    def _pdir(self, project_title: str) -> Path:
        return self.root / _safe(project_title, 60)

    # --- notes ----------------------------------------------------------------
    def _hyp_note(self, h: dict[str, Any]) -> str:
        c = h.get("confrontation") or {}
        ver = int(h.get("version", 1))
        out = _fm({"type": "hipotesis", "tag": h.get("tag", ""), "version": ver,
                   "status": h.get("status", ""), "kind": h.get("kind", ""),
                   "lit_status": h.get("lit_status", "PENDING"),
                   "synced": now_iso()})
        out += _BANNER
        out += f"\n# {h.get('tag','')} (v{ver}): {h.get('title','')}\n\n"
        if h.get("trigger_question"):
            out += f"**Pregunta detonante:** {h['trigger_question']}\n\n"
        for label, key in (("Argumento", "argument"), ("Duda", "doubt"),
                           ("Idea de prueba", "test_idea")):
            if h.get(key):
                out += f"**{label}:** {h[key]}\n\n"
        if h.get("approval_reason"):
            out += f"**Razón de aprobación:** {h['approval_reason']}\n\n"
        if c:
            out += "## ⚖️ Confrontación con la literatura\n\n"
            if c.get("query_used"):
                out += f"- Búsqueda ejecutada: `{c['query_used']}`\n"
            out += f"- Postura de la evidencia: **{c.get('stance','')}**\n\n"
            if c.get("argument_for"):
                out += f"**A favor:** {c['argument_for']}\n\n"
            if c.get("argument_against"):
                out += f"**En contra:** {c['argument_against']}\n\n"
            if c.get("improved_hypothesis"):
                out += f"**Hipótesis mejorada:** {c['improved_hypothesis']}\n\n"
            cites = c.get("citations") or []
            if cites:
                out += "**Literatura leída:**\n"
                out += "".join(f"- [[{_safe(x.get('title',''))}]]\n" for x in cites)
                out += "\n"
            ideas = c.get("experiment_ideas") or []
            if ideas:
                out += "## 🧪 Cómo comprobarlo (ejecutable en la compu)\n\n"
                for i in ideas:
                    out += (f"- **{i.get('title','')}** [{i.get('method_type','')}] — "
                            f"{i.get('approach','')} (datos: {i.get('data_source','')})\n")
                out += "\n"
        hist = h.get("history") or []
        if hist:
            out += "## 🗂 Versiones anteriores\n\n"
            for v in hist:
                out += f"- v{v.get('version')}: {v.get('title','')}\n"
            out += "\n"
        return out

    def _paper_note(self, p: dict[str, Any]) -> str:
        out = _fm({"type": "paper", "doi": p.get("doi", ""),
                   "source": p.get("source", ""),
                   "relevance": p.get("relevance") or "",
                   "integrity": p.get("integrity", ""),
                   "hyp": p.get("angle", ""), "synced": now_iso()})
        out += _BANNER
        out += f"\n# {p.get('title','')}\n\n"
        if p.get("authors"):
            out += f"**Autores:** {', '.join(p['authors'])}\n\n"
        url = p.get("url") or (f"https://doi.org/{p['doi']}" if p.get("doi") else "")
        if url:
            out += f"**Fuente:** [{p.get('source','link')}]({url})\n\n"
        if p.get("integrity") == "retracted":
            out += "> [!danger] RETRACTADO — no citar como evidencia.\n\n"
        if p.get("abstract"):
            out += f"## Abstract\n\n{p['abstract']}\n\n"
        if p.get("topics"):
            out += "**Temas:** " + ", ".join(p["topics"]) + "\n\n"
        if p.get("angle"):
            out += f"Vinculado a la hipótesis [[{p['angle']}]].\n"
        return out

    def _exp_note(self, e: dict[str, Any]) -> str:
        out = _fm({"type": "experimento", "hyp": e.get("hyp_tag", ""),
                   "status": e.get("status", ""),
                   "method_type": e.get("method_type", ""), "synced": now_iso()})
        out += _BANNER
        out += f"\n# ⚗️ {e.get('title','')}\n\n"
        for label, key in (("Qué mide", "what"), ("Cómo", "how"),
                           ("Datos", "data_source"), ("Controles", "controls"),
                           ("Discriminador", "discriminator")):
            if e.get(key):
                out += f"**{label}:** {e[key]}\n\n"
        if e.get("claim"):
            out += f"## Resultado (real)\n\n{e['claim']}\n\n"
        elif e.get("plan"):
            out += f"## Plan reproducible (PENDIENTE — no es un resultado)\n\n{e['plan']}\n\n"
        if e.get("hyp_tag"):
            out += f"Experimento de la hipótesis [[{e['hyp_tag']}]].\n"
        return out

    def _project_note(self, title: str, domain: str, hyps: list[dict[str, Any]],
                      papers: list[dict[str, Any]], exps: list[dict[str, Any]]) -> str:
        out = _fm({"type": "proyecto", "domain": domain, "synced": now_iso()})
        out += _BANNER
        out += f"\n# 🔬 {title}\n\n**Dominio:** {domain}\n\n## Hipótesis\n\n"
        for h in hyps:
            st = (h.get("status") or "").upper()
            mark = {"APPROVED": "✅", "REJECTED": "❌"}.get(st, "⬜")
            out += (f"- {mark} [[{h.get('tag','')}]] (v{int(h.get('version',1))}) "
                    f"{h.get('title','')[:90]}\n")
        out += f"\n## Literatura ({len(papers)} papers reales)\n\n"
        for p in papers[:50]:
            out += f"- [[{_safe(p.get('title',''))}]] ({p.get('source','')})\n"
        out += f"\n## Experimentos ({len(exps)})\n\n"
        for e in exps:
            out += f"- [{e.get('status','')}] [[{_safe('EXP ' + (e.get('title') or ''))}]]\n"
        return out

    # --- sync -----------------------------------------------------------------
    def sync_project(self, project_id: str, session_factory: Any | None = None
                     ) -> dict[str, Any]:
        with _SYNC_LOCK:
            return self._sync_project_locked(project_id, session_factory)

    def _sync_project_locked(self, project_id: str, session_factory: Any | None = None
                             ) -> dict[str, Any]:
        from ..discovery.store import DiscoveryStore
        from ..ledger.db import default_session_factory
        from ..ledger.service import ResearchLedger
        sf = session_factory or default_session_factory()
        ledger = ResearchLedger(sf)
        p = ledger.get_project(project_id)
        if p is None:
            return {"ok": False, "error": "project not found"}
        store = DiscoveryStore(sf, ledger)
        hyps = store.list_objects(project_id, kind="candidate")
        papers = store.list_objects(project_id, kind="literature")
        exps = store.list_objects(project_id, kind="experiment")

        self._ensure_vault()
        pdir = self._pdir(p.title)
        n = 0
        for sub in ("Hipotesis", "Literatura", "Experimentos"):
            (pdir / sub).mkdir(parents=True, exist_ok=True)
        (pdir / "_Proyecto.md").write_text(
            self._project_note(p.title, p.domain or "", hyps, papers, exps),
            encoding="utf-8")
        n += 1
        for h in hyps:
            tag = h.get("tag") or h.get("id", "")[:8]
            (pdir / "Hipotesis" / f"{_safe(tag)}.md").write_text(
                self._hyp_note(h), encoding="utf-8")
            n += 1
        seen: set[str] = set()
        for pp in papers:
            fname = _safe(pp.get("title", "") or pp.get("doi", "") or pp.get("id", ""))
            if fname in seen:            # same paper indexed for several hypotheses
                continue
            seen.add(fname)
            (pdir / "Literatura" / f"{fname}.md").write_text(
                self._paper_note(pp), encoding="utf-8")
            n += 1
        for e in exps:
            fname = _safe("EXP " + (e.get("title") or e.get("id", "")))
            (pdir / "Experimentos" / f"{fname}.md").write_text(
                self._exp_note(e), encoding="utf-8")
            n += 1
        return {"ok": True, "vault": str(self.root), "project_dir": str(pdir),
                "notes_written": n}


def sync_project_best_effort(project_id: str, session_factory: Any | None = None) -> None:
    """Fire-and-forget sync used inside the research flow — never breaks the flow."""
    try:
        ObsidianExporter().sync_project(project_id, session_factory)
    except Exception:  # noqa: BLE001 - vault sync must never break research
        pass
