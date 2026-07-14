# Pre-chequeo Sprint 8 (World Model Engine)

**Fecha:** 2026-07-13
**Rama de partida:** `feature/acero-sprints-5-7-discovery-engine` (commit `c5c3695`).
**Rama de trabajo:** `feature/acero-sprint-8-world-model`.

## Estado verificado
- `git status`: árbol limpio.
- Base: Sprints 1–7 (194 tests verdes, ruff+mypy limpios, Docker + Codex operativos).
- El Discovery Engine ya produce hipótesis, experimentos, resultados, confianza,
  negativos y procedencia — todo esto ALIMENTARÁ el World Model.

## Dataset real autorizado (astronomía)
- **Fuente:** NASA Exoplanet Archive (TAP), tabla `ps` (Planetary Systems).
- **Consulta:** `pl_name, pl_orbper (días), pl_orbsmax (AU), st_mass (M_sun)` con
  `default_flag=1` y valores no nulos.
- **Licencia:** dominio público (NASA/IPAC/Caltech).
- **Procedencia verificable:** la URL TAP exacta se registra; se calcula hash del
  CSV descargado.
- **Tamaño:** pequeño (< 1 MB filtrado; muy por debajo de 500 MB).
- **Referencia científica:** NASA Exoplanet Archive (Akeson et al. 2013, PASP 125).
- **Conectividad confirmada** en la Fase 0.
- **Uso:** comprobar que el World Model **cambia correctamente** al testear la
  creencia "se cumple la tercera ley de Kepler (P² ∝ a³/M)" con datos reales. NO se
  afirma ningún descubrimiento nuevo.

## Arquitectura elegida
Paquete `src/acero/world_model/`: nodos epistémicos (creencias), aristas tipadas,
estado de creencia configurable, grafo persistente y versionado, consultas de
memoria científica, motor de contradicciones, motor de anomalías, programas de
investigación, evolución del conocimiento, ingestión de datos reales y
visualización HTML. Persistencia en tablas nuevas `world_nodes`/`world_edges`
(`ledger/models.py`). Integración: los resultados del Discovery Engine se aplican
al World Model vía `world_model/update.py`.

## Política aplicada
Descarga puntual autorizada por el usuario (`large_downloads` sigue false por
defecto; esta descarga es < 1 MB y aprobada explícitamente). Sin credenciales, sin
servicios de pago, sin publicación.
