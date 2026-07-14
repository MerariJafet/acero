# Tool Creation Pipeline (Sprint 7.6)

Source: `discovery/tool_creation.py`. Codex (or a mock) may PROPOSE a scientific
tool, but a generated tool cannot be used in any conclusion until it passes every
gate.

## Gates
```
proposal
  → static screen (execution policy + path-traversal/sensitive-path block)
    → benchmark present (self_test must report passed/total)
      → sandbox execution of code + self-test (MANDATORY; nothing runs unsandboxed)
        → all benchmark cases pass
          → approval (APPROVED) else QUARANTINED
            → tool registry (provenance recorded)
```

A tool that fails any gate is **QUARANTINED** and `is_usable()` returns False.

## Security properties (tested in `tests/security/test_tool_creation.py`)
- Invalid code → sandbox status ≠ ok → rejected.
- Failing self-test → `benchmark.all_passed = False` → rejected.
- Missing benchmark → not approvable.
- **Path traversal** (`../`, `/etc/`, `/proc/`, …) → screened and refused.
- **Network** (`socket`, `urllib`, …) → screened; the sandbox also blocks it.
- Quarantined tools are not usable.

## Provenance
The registry records name, code, self-test, version, provider, model, prompt
version, evaluation stages, and limitations. `human_author_required` is always
true — a human authorises real use. Recommended backend for untrusted generated
code: the Docker sandbox (`--network=none --read-only --cap-drop=ALL`).
