"""Docker sandbox backend tests. Skipped cleanly when Docker/image unavailable."""

from __future__ import annotations

import pytest

from acero.sandbox.docker_runner import DockerRunner, docker_available, image_present

pytestmark = pytest.mark.security

_HAVE_DOCKER = docker_available() and image_present()
requires_docker = pytest.mark.skipif(
    not _HAVE_DOCKER, reason="Docker or acero-sandbox image not available"
)


@pytest.fixture()
def runner():
    return DockerRunner()


@requires_docker
def test_docker_basic_and_numpy(runner, tmp_path):
    res = runner.run(
        "import json, numpy as np; print(json.dumps({'s': int(np.arange(5).sum())}))",
        tmp_path, timeout_sec=60,
    )
    assert res.status == "ok"
    assert '"s": 10' in res.stdout


@requires_docker
def test_docker_network_isolated(runner, tmp_path):
    code = (
        "mod = 'soc' + 'ket'\n"
        "import importlib; m = importlib.import_module(mod)\n"
        "try:\n"
        "    m.create_connection(('1.1.1.1', 80), timeout=2); print('CONNECTED')\n"
        "except OSError:\n"
        "    print('BLOCKED')\n"
    )
    res = runner.run(code, tmp_path, timeout_sec=60)
    assert res.status == "ok"
    assert "BLOCKED" in res.stdout and "CONNECTED" not in res.stdout


@requires_docker
def test_docker_no_host_secrets(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "top-secret")
    res = runner.run(
        "import os; print('KEY=' + os.environ.get('ANTHROPIC_API_KEY', 'ABSENT'))",
        tmp_path, timeout_sec=60,
    )
    assert "KEY=ABSENT" in res.stdout
    assert "top-secret" not in res.stdout


@requires_docker
def test_docker_screening_refuses(runner, tmp_path):
    res = runner.run("import os; os.system('id')", tmp_path)
    assert res.status == "refused"


@requires_docker
def test_docker_timeout(runner, tmp_path):
    res = runner.run("while True:\n    pass", tmp_path, timeout_sec=4)
    assert res.status == "timeout"
    assert res.exit_code == 124


def test_get_runner_docker_fallback_when_unavailable():
    # get_runner(non-strict) must always return a usable runner.
    from acero.sandbox.runner import SubprocessRunner, get_runner

    r = get_runner("docker")
    assert hasattr(r, "run")
    if not _HAVE_DOCKER:
        assert isinstance(r, SubprocessRunner)
