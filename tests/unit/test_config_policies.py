import pytest

from acero.core.config import Config, load_config
from acero.core.errors import PolicyViolation
from acero.policies.guard import CostRequest, PolicyGuard
from acero.policies.loader import REQUIRED_POLICIES, load_policies


def test_all_policies_load():
    bundle = load_policies()
    for name in REQUIRED_POLICIES:
        assert name in bundle.policies
        assert bundle.policies[name]["policy"] == name


def test_config_defaults_and_db_url():
    cfg = load_config(env="development")
    assert cfg.app.name == "ACERO"
    assert cfg.abs_db_url().startswith("sqlite:////")  # absolute path resolved


def test_default_db_url_prefers_workspace_over_repo(tmp_path, monkeypatch):
    """2026-08-20: tras migrar acero_data/ fuera del repo, abs_db_url() seguía
    resolviendo sqlite:///acero_data/acero.sqlite contra repo_root() -- cada
    reinicio del portal creaba una base NUEVA Y VACÍA dentro del repo, dejando el
    workspace real (~/ACERO) invisible sin ningún error. Con ACERO_HOME apuntando
    a un workspace fresco (sin legado), la ruta resuelta debe caer DENTRO de ese
    workspace, nunca en acero_data/ del repo.

    Config() directo (no load_config/get_config): el fixture autouse de conftest
    fija ACERO_DB_URL a una ruta de test para TODOS los tests -- lo correcto ahí,
    pero invisibiliza justo la rama que este test necesita ejercitar."""
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "workspace"))
    cfg = Config()  # storage.db_url por defecto: sqlite:///acero_data/acero.sqlite
    url = cfg.abs_db_url()
    assert url.startswith("sqlite:////")
    assert str(tmp_path / "workspace") in url
    assert "acero_data" not in url


def test_data_path_falls_back_to_legacy_if_workspace_unmigrated(tmp_path,
                                                                  monkeypatch):
    """La misma lógica de la que abs_db_url() depende: instalación vieja sin
    migrar -- el workspace no tiene datos pero el legado sí -- debe seguir
    usando el legado (con aviso), nunca perder el estado ni crear uno vacío."""
    monkeypatch.setenv("ACERO_HOME", str(tmp_path / "workspace"))
    legacy = tmp_path / "repo" / "acero_data" / "acero.sqlite"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("marca que 'existe'", encoding="utf-8")
    from acero.core.workspace import data_path
    resolved = data_path("datos/acero.sqlite", legacy=legacy)
    assert resolved == legacy


def test_paid_llm_disabled_by_default():
    guard = PolicyGuard()
    assert guard.paid_llm_allowed() is False


def test_cost_guard_blocks_paid_action():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_cost(CostRequest(action="call_gpt", estimated_cost_usd=0.5))


def test_cost_guard_circuit_breaker_trips_on_first_request():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_cost(CostRequest(action="paid_call", request_count=1))


def test_cost_guard_allows_zero_cost_local_action():
    guard = PolicyGuard()
    guard.check_cost(CostRequest(action="local_compute", estimated_cost_usd=0.0))


def test_autonomy_forbidden_and_required():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.require_autonomous("activate_paid_llm")  # forbidden
    with pytest.raises(PolicyViolation):
        guard.require_autonomous("git_push")  # human_required
    guard.require_autonomous("run_sandboxed_code")  # auto -> no raise


def test_research_domain_guard():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_research_domain("wet_lab_biology")
    guard.check_research_domain("mathematical_modeling")  # allowed


def test_publication_requires_human_review():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_publication(human_reviewed=False)
    guard.check_publication(human_reviewed=True)
