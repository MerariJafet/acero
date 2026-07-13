# ADR-0001: Monolito modular en lugar de microservicios

- **Estado:** Aceptado
- **Fecha:** 2026-07-12

## Contexto
La misión pide una arquitectura modular pero advierte explícitamente contra
microservicios innecesarios. El repositorio estaba vacío (sin base previa).

## Decisión
Construir ACERO como un único paquete Python instalable (`src/acero/`) con
fronteras de módulo claras (core, epistemology, ledger, literature, experiment,
sandbox, llm, cli, api). Una sola base de datos SQLite por defecto.

## Consecuencias
- (+) Despliegue y pruebas triviales; sin orquestación de red; local-first.
- (+) Refactor a servicios posible más adelante si un módulo lo justifica.
- (−) Aislamiento de fallos más débil que procesos separados (mitigado por el
  sandbox para ejecución de código no confiable).
