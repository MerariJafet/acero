import pytest

from acero.sandbox.runner import SubprocessRunner
from acero.sandbox.screen import screen_code


@pytest.fixture()
def runner():
    return SubprocessRunner()


def test_basic_execution_captures_stdout(runner, tmp_path):
    res = runner.run("print('hello acero')", tmp_path)
    assert res.status == "ok"
    assert res.exit_code == 0
    assert "hello acero" in res.stdout


def test_nonzero_exit_is_failed(runner, tmp_path):
    res = runner.run("import sys; sys.exit(3)", tmp_path)
    assert res.status == "failed"
    assert res.exit_code == 3


def test_screening_refuses_dangerous_code(runner, tmp_path):
    res = runner.run("import os; os.system('echo pwned')", tmp_path)
    assert res.status == "refused"
    assert res.screen_matches


def test_screen_function_flags_patterns():
    assert not screen_code("s = socket.socket()").allowed
    assert not screen_code("import os; os.system('ls')").allowed
    assert screen_code("x = 1 + 1").allowed


def test_timeout_is_enforced(runner, tmp_path):
    res = runner.run("while True:\n    pass", tmp_path, timeout_sec=2)
    assert res.status == "timeout"
    assert res.timed_out
    assert res.exit_code == 124


def test_network_blocked_at_runtime(runner, tmp_path):
    # 'socket' literal is screened; use a runtime path that avoids the literal
    # by building the module name dynamically, proving the runtime guard works.
    code = (
        "mod = 'soc' + 'ket'\n"
        "import importlib\n"
        "m = importlib.import_module(mod)\n"
        "try:\n"
        "    m.create_connection(('example.com', 80), timeout=1)\n"
        "    print('CONNECTED')\n"
        "except OSError as e:\n"
        "    print('BLOCKED:', e)\n"
    )
    res = runner.run(code, tmp_path)
    assert res.status == "ok"
    assert "BLOCKED" in res.stdout
    assert "CONNECTED" not in res.stdout


def test_secrets_not_leaked_into_sandbox(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret-value")
    code = "import os; print('KEY=' + os.environ.get('ANTHROPIC_API_KEY', 'ABSENT'))"
    res = runner.run(code, tmp_path)
    assert "KEY=ABSENT" in res.stdout
    assert "super-secret-value" not in res.stdout


def test_writes_confined_to_workspace(runner, tmp_path):
    code = (
        "from pathlib import Path\n"
        "p = Path('out.txt'); p.write_text('ok')\n"
        "print(p.resolve())\n"
    )
    res = runner.run(code, tmp_path)
    assert res.status == "ok"
    assert str(tmp_path) in res.stdout
