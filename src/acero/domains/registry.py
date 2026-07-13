"""Registry of domain plugins."""

from __future__ import annotations

from ..policies.guard import PolicyGuard
from .astronomy import AstronomyPlugin
from .base import DomainPlugin
from .chemistry import ChemistryPlugin
from .genetics import GeneticsPlugin
from .physics import PhysicsPlugin

_PLUGINS: dict[str, DomainPlugin] = {
    p.name: p for p in (PhysicsPlugin(), AstronomyPlugin(), GeneticsPlugin(), ChemistryPlugin())
}


def all_plugins() -> list[DomainPlugin]:
    return list(_PLUGINS.values())


def plugin_names() -> list[str]:
    return sorted(_PLUGINS)


def get_plugin(name: str, guard: PolicyGuard | None = None) -> DomainPlugin:
    if name not in _PLUGINS:
        raise KeyError(f"Unknown domain '{name}'. Available: {plugin_names()}")
    # Safety gate: the plugin's domain must not be a forbidden research domain.
    guard = guard or PolicyGuard()
    guard.check_research_domain(name)  # forbidden domains (wet-lab etc.) are not plugin names
    return _PLUGINS[name]


def run_all_benchmarks() -> dict[str, dict]:
    return {p.name: p.benchmark().to_dict() for p in all_plugins()}
