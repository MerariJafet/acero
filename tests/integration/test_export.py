import json

from acero.core.ids import new_id
from acero.epistemology.schemas import Hypothesis, ResearchQuestion
from acero.ledger.export import build_dossier, export_project


def test_export_produces_hashed_dossier(ledger, project, tmp_path):
    q = ledger.add_entity(ResearchQuestion(id=new_id("q"), project_id=project.id, title="Q?"))
    ledger.add_entity(Hypothesis(id=new_id("hyp"), project_id=project.id,
                                 question_id=q.id, title="H1"))
    paths = export_project(ledger, project.id, tmp_path)
    assert paths["dir"] == str(tmp_path)

    dossier = json.loads((tmp_path / "dossier.json").read_text())
    assert dossier["project"]["id"] == project.id
    assert dossier["counts"]["QUESTION"] == 1
    assert dossier["counts"]["HYPOTHESIS"] == 1

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "dossier.json" in manifest["files"]
    assert manifest["files"]["dossier.json"].startswith("sha256:")
    assert (tmp_path / "dossier.md").exists()
    assert (tmp_path / "checksums.txt").exists()


def test_build_dossier_includes_provenance(ledger, project):
    ledger.add_entity(ResearchQuestion(id=new_id("q"), project_id=project.id, title="Q?"))
    d = build_dossier(ledger, project.id)
    assert d["provenance"], "dossier must include the provenance trail"
