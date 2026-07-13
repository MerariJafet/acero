# Plugins de dominio científico (Sprint 10 — inicial)

Framework en `src/acero/domains/`. Cada plugin declara unidades, herramientas
**solo computacionales**, validaciones, simuladores deterministas, una plantilla
de proyecto y un **benchmark de respuesta conocida**. Regla dura: **sin
laboratorio húmedo**, sin procedimientos físicos/biológicos/químicos; los dominios
peligrosos están prohibidos por `policies/research_safety.yaml`.

| Dominio | Herramientas | Benchmark (respuesta conocida) |
|---|---|---|
| **physics** | projectile_range, newton_cooling, damped_oscillator_period | 45° maximiza alcance; vida media (k=ln2)=1; periodo no amortiguado=1 |
| **astronomy** | kepler_period, circular_orbital_velocity, magnitude_distance | Tierra P=1 yr; a=4 AU → P=8 yr; módulo de distancia m=M → 10 pc |
| **genetics** | gc_content, transcribe, translate, hardy_weinberg | GC=0.5; HW p=0.6 → 0.36/0.48/0.16; ATG AAA TAA → "MK" |
| **chemistry** | molar_mass, ideal_gas, moles_from_mass | M(H₂O)=18.015; M(CO₂)=44.009; volumen molar STP≈0.0224 m³ |

Total: **14 casos de benchmark**, todos verdes.

## Uso

```bash
acero domain list
acero domain info physics
acero domain benchmark            # todos
acero domain benchmark --name chemistry
```

```python
from acero.domains.registry import get_plugin
phys = get_plugin("physics")
phys.simulate("projectile_range", {"v0": 20, "angle_deg": 30})   # -> {'range_m': ...}
phys.validate("projectile", {"angle_deg": 120})                   # -> invalid
```

API: `GET /domains`, `GET /domains/{name}/benchmark`.

## Qué falta (Sprint 10 completo)
- Más simuladores por dominio, unidades con conversión estricta, y datasets de
  referencia por dominio.
- Integración de los simuladores como "herramientas permitidas" dentro del ciclo
  de experimentos (`experiment/`) por dominio.
- Benchmarks más amplios y validación de propiedades físicas (dimensional).
