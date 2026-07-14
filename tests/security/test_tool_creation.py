"""Sprint 7.6 tests: controlled tool-creation pipeline (security-critical)."""

from __future__ import annotations

import pytest

from acero.discovery.tool_creation import (
    ToolProposal,
    ToolRegistry,
    evaluate_tool,
    screen_tool_code,
)

pytestmark = pytest.mark.security

GOOD_TOOL = ToolProposal(
    name="gcd", rationale="greatest common divisor helper",
    code="def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n",
    self_test=(
        "import json\n"
        "cases = [((12, 8), 4), ((100, 10), 10), ((17, 5), 1)]\n"
        "passed = sum(1 for (a, b), exp in cases if gcd(a, b) == exp)\n"
        "print(json.dumps({'passed': passed, 'total': len(cases)}))\n"
    ),
)


def test_good_tool_is_approved_and_registered(disc_store, project):
    ev = evaluate_tool(GOOD_TOOL)
    assert ev.approved
    reg = ToolRegistry(disc_store, project.id)
    payload = reg.register(GOOD_TOOL, ev)
    assert payload["status"] == "APPROVED"
    assert reg.is_usable(payload["id"])
    # Provenance + version recorded.
    assert payload["version"] == 1
    assert payload["provenance"]["provider"] == "mock"


def test_invalid_code_rejected():
    bad = ToolProposal(name="broken", rationale="x",
                       code="def f(:\n    return", self_test="print({'passed':1,'total':1})")
    ev = evaluate_tool(bad)
    assert not ev.approved
    assert ev.stages["sandbox"]["status"] != "ok"


def test_failing_test_rejected():
    failing = ToolProposal(
        name="wrong", rationale="x", code="def add(a, b):\n    return a - b\n",
        self_test=("import json\n"
                   "passed = 1 if add(2, 2) == 4 else 0\n"
                   "print(json.dumps({'passed': passed, 'total': 1}))\n"))
    ev = evaluate_tool(failing)
    assert not ev.approved
    assert ev.stages["benchmark"]["all_passed"] is False


def test_tool_without_benchmark_not_approved():
    no_bench = ToolProposal(name="nb", rationale="x",
                            code="def f():\n    return 1\n", self_test="print('hello')\n")
    ev = evaluate_tool(no_bench)
    assert not ev.approved
    assert ev.stages["benchmark_present"]["ok"] is False


def test_path_traversal_blocked():
    ok, matches = screen_tool_code("open('../../etc/passwd').read()")
    assert not ok
    assert "path_traversal" in matches
    ev = evaluate_tool(ToolProposal(name="pt", rationale="x",
                                    code="data = open('../../etc/passwd').read()\n",
                                    self_test="print({'passed':1,'total':1})"))
    assert not ev.approved


def test_network_access_blocked_by_screen():
    ok, matches = screen_tool_code("import socket\ns = socket.socket()")
    assert not ok


def test_quarantined_tool_not_usable(disc_store, project):
    failing = ToolProposal(name="wrong2", rationale="x",
                           code="def add(a, b):\n    return a - b\n",
                           self_test="import json\nprint(json.dumps({'passed':0,'total':1}))\n")
    ev = evaluate_tool(failing)
    reg = ToolRegistry(disc_store, project.id)
    payload = reg.register(failing, ev)
    assert payload["status"] == "QUARANTINED"
    assert not reg.is_usable(payload["id"])
