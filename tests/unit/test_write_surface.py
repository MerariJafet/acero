"""Sprint 11 architecture test: only boundary modules touch persistence directly.

Fails if a non-authorized module imports the ORM row classes (`ledger.models`) or the raw
`DiscoveryRow`/`WorldNodeRow` mutation surface directly — mutations must go through the
stores/boundary services (which the inline gate guards).
"""

from __future__ import annotations

import ast
from pathlib import Path

from acero.core.config import repo_root

# Modules allowed to import persistence ORM classes directly (the boundary layer).
ALLOWED_PREFIXES = (
    "acero/ledger/",            # the persistence layer itself
    "acero/discovery/store",    # discovery boundary store
    "acero/world_model/",       # world model graph (guarded mutations)
    "acero/understanding/store",
    "acero/literature/",
)

FORBIDDEN_IMPORTS = {"acero.ledger.models"}


def _iter_py() -> list[Path]:
    src = repo_root() / "src" / "acero"
    return [p for p in src.rglob("*.py") if "__pycache__" not in str(p)]


def test_only_boundary_modules_import_persistence():
    src_root = repo_root() / "src"
    offenders: list[str] = []
    for path in _iter_py():
        rel = str(path.relative_to(src_root)).replace("\\", "/")
        if any(rel.startswith(pref) for pref in ALLOWED_PREFIXES):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
            elif isinstance(node, ast.Import):
                mod = ",".join(a.name for a in node.names)
            if mod and any(f in mod for f in FORBIDDEN_IMPORTS):
                offenders.append(f"{rel}: imports {mod}")
    assert not offenders, "non-boundary modules import persistence directly:\n" + \
        "\n".join(offenders)


def test_boundary_layer_is_nonempty():
    # sanity: the allowed boundary modules actually exist
    src_root = repo_root() / "src"
    assert (src_root / "acero" / "ledger" / "models.py").exists()
    assert (src_root / "acero" / "discovery" / "store.py").exists()
