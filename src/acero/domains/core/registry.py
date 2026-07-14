"""Registry of Scientific Domain Labs."""

from __future__ import annotations

from ..astronomy.lab import AstronomyLab
from ..chemistry.lab import ChemistryLab
from ..genetics.lab import GeneticsLab
from ..physics.lab import PhysicsLab
from .contracts import DomainLab

_LABS: dict[str, DomainLab] = {
    "physics": PhysicsLab(),
    "astronomy": AstronomyLab(),
    "genetics": GeneticsLab(),
    "chemistry": ChemistryLab(),
}


def lab_names() -> list[str]:
    return sorted(_LABS)


def get_lab(name: str) -> DomainLab:
    if name not in _LABS:
        raise KeyError(f"unknown domain lab {name!r}; have {lab_names()}")
    return _LABS[name]


def all_labs() -> list[DomainLab]:
    return [_LABS[n] for n in lab_names()]


def run_all_benchmarks() -> dict[str, dict]:
    return {name: get_lab(name).benchmark() for name in lab_names()}
