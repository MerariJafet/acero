# Sprint 10 — Scientific Domain Labs + Inline Gate + Hybrid Grader · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprint-10-scientific-domain-labs`

## Parte A — Gate epistémico in-line (obligatorio)
- `enforce()` corre el gate ANTES de la mutación; si bloquea, **no hay mutación** y se
  guarda un registro de rechazo (el intento no se pierde). Provenance y gate result se
  registran siempre.
- **Seguridad transaccional**: sin estado parcial; rollback probado; contexto de gate
  thread-local; una escritura protegida cruda fuera del contexto lanza `BypassDetected`.
- **Rutas protegidas**: World Model `update_belief` / `link` (conocimiento aceptado), vía
  `GatedWorldModel`. Otras rutas quedan como deuda de Sprint 11 (documentado).
- **Overrides**: NO_OVERRIDE / HUMAN / ADMIN / EXTERNAL_REVIEW; reglas **no
  overridables** (cita inventada, resultado fabricado/leakage, secreto, ejecución
  insegura, procedencia perdida, edición retroactiva, autoría falsa, borrar negativos,
  Codex-como-evidencia, confianza=1, integridad de publicación).
- **Observabilidad**: métricas (evaluadas/permitidas/bloqueadas/warnings/overrides/
  rollbacks/bypass) + trazas; **benchmark de bypass (7/7 bloqueados)**.

## Parte B — Scientific Domain Labs
- Contrato `ScientificDomain` (ontología, conceptos, unidades, escalas, modelos, term
  libraries, solvers, datasets, reglas de dominio, clase de seguridad, capacidades,
  límites) + **clasificación de resultado** (una simulación nunca es validación física).
- **Física**: term library dimensional extendida + solvers auditables (RK4, simpléctico,
  FTCS, leapfrog) con estabilidad CFL/energía; benchmark 8/8 (incl. solver inestable →
  falsa evidencia detectada).
- **Astronomía**: Lomb–Scargle, autocorrelación, gaps/alias/red-noise/FAP; 8/8 (incl.
  periodicidad-sin-mecanismo → abstención).
- **Genética** (RESTRINGIDA): Hardy–Weinberg, selección/deriva, confusión por estructura,
  corrección múltiple, Hill/latente; 8/8; causalidad espuria **bloqueada**; peticiones
  peligrosas rechazadas.
- **Química** (RESTRINGIDA): cinética, reversible, Michaelis–Menten, Arrhenius, masa,
  rigidez, no identificabilidad; 8/8; violación de estequiometría **bloqueada**;
  predicciones etiquetadas NOT_EXPERIMENTALLY_VALIDATED.

## Parte C — Grader híbrido
- Pipeline determinista (autoridad) → forbidden → contradicción → consistencia →
  semántico advisory (Codex) → agregación → nota + incertidumbre + propuesta de estado.
- Codex nunca certifica dominio: puede elevar una paráfrasis válida a PASS_WITH_REVIEW
  **solo** con un fragmento citado real, jamás a PASS/MASTERED.
- Calibración (10 fixtures): acuerdo 0.9, **0 falsos positivos**. Adversarial (inyección,
  copia de rúbrica, grandilocuencia, confianza vacía, otra pregunta, repetición): no
  engaña ni con un mock semántico permisivo.

## Benchmark integral
Multi-Domain (4 tracks + transferencia): 8/8 por dominio; el gate bloquea evidencia falsa,
causalidad desde asociación, y violación de estequiometría; transferencia reconoce
estructura compartida sin identidad. Gate-bypass: 7/7 bloqueados.

## Auditoría (Codex real)
Grader: Codex real reconoció una paráfrasis genuina (→ PASS_WITH_REVIEW, sin dominio) y
falló una respuesta segura-pero-vacía. Gate: **12 hallazgos**; correcciones verificables
con regresión: (A) reglas de integridad de publicación **no overridables**; (B) la
elevación por paráfrasis exige **fragmento citado** real. Limitaciones declaradas: superficie
protegida acotada al World Model; contexto thread-local no cruza async/subproceso.

## Calidad
**494 pruebas en verde** (+66), ruff limpio, mypy limpio (234 archivos), `make verify` OK.

## Honestidad científica
Capacidades reales: cálculo/simulación/ajuste/inferencia estadística por dominio. Los
resultados son SIMULADOS o ajustados; ningún mecanismo fue demostrado experimentalmente;
los datasets son públicos y gated; las herramientas son aproximadas (1-D, QSSA, dos
cuerpos). **Cuatro laboratorios computacionales NO equivalen a cuatro laboratorios
físicos**: no hay validación física/biológica/química y toda validación requiere
colaboración institucional.
