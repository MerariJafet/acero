"""Obsidian vault exporter: structured notes from the research flow (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.obsidian_sync import ObsidianExporter, _safe


def test_safe_filenames():
    assert _safe('a/b:c*d?"<>|#^[]') == "a b c d"
    assert _safe("") == "sin-titulo"
    assert len(_safe("x" * 300)) <= 80


def test_sync_project_writes_linked_notes(session_factory, tmp_path):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Vault test", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "vale la pena")
    fl.store.update_payload(h["id"], {"confrontation": {
        "stance": "mixed", "argument_for": "af", "argument_against": "ac",
        "improved_hypothesis": "mejor", "query_used": "cmb anomaly",
        "citations": [{"title": "Paper A", "doi": "10.1/x", "source": "openalex"}],
        "experiment_ideas": [{"title": "Bajar Planck", "approach": "descargar",
                              "data_source": "ESA PLA", "method_type": "download_data",
                              "feasible_local": True}]}})
    fl.propose_experiments(p.id, h["id"], use_ai=False)

    res = ObsidianExporter(tmp_path / "vault").sync_project(p.id, session_factory)
    assert res["ok"] is True and res["notes_written"] >= 3

    pdir = tmp_path / "vault" / "Vault test"
    proj = (pdir / "_Proyecto.md").read_text(encoding="utf-8")
    tag = h["tag"]
    assert f"[[{tag}]]" in proj                       # project links hypothesis
    hyp = (pdir / "Hipotesis" / f"{tag}.md").read_text(encoding="utf-8")
    assert "Confrontación" in hyp and "[[Paper A]]" in hyp
    assert "Bajar Planck" in hyp                      # experiment ideas included
    exps = list((pdir / "Experimentos").glob("*.md"))
    assert exps and f"[[{tag}]]" in exps[0].read_text(encoding="utf-8")
    # vault skeleton exists (Home + .obsidian marker)
    assert (tmp_path / "vault" / "Home.md").exists()
    assert (tmp_path / "vault" / ".obsidian").is_dir()


def test_sync_missing_project(session_factory, tmp_path):
    res = ObsidianExporter(tmp_path / "v").sync_project("nope", session_factory)
    assert res["ok"] is False
