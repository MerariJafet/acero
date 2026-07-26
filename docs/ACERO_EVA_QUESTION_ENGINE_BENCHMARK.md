# ACERO — Benchmark EVA / Motor de Preguntas (heurístico vs Codex específico)

Valida que el EVA específico por hipótesis **cambia decisiones**, no que produce más texto.
Corrido en vivo con Codex real sobre las 6 hipótesis rivales del re-análisis del valle de
radios (`proj_01KYDVD6HTJXEQD3RS56DB7WEP`). Código: `src/acero/portal/eva_benchmark.py`
(offline dado un extractor; inyectable con Codex para estos números).

## Resultados (6 hipótesis)

| Métrica | Heurístico | **Codex específico** | Mejor |
|---|---|---|---|
| `confounding_coverage` (fracción de claims donde se detecta CONFUSIÓN) | 0.00 | **1.00** | Codex |
| `assumption_vulns_per_claim` (supuestos concretos por claim) | 3.0 | **7.0** | Codex |
| `content_distinctness` (1 − duplicados por CONTENIDO) | 0.333 | **1.00** | Codex |
| `generic_question_rate` (preguntas con placeholder «la exposición/el outcome») | 0.00 | 0.00 | empate (ya arreglado) |
| `type_distinctness` (1 − duplicados por TIPO) | 0.167 | 0.00 | — (ver nota) |

## Lectura

- **La confusión — el eje central de este caso — sólo la detecta el Codex path** (0 → 100 %).
  La heurística no puede inferir exposición/outcome, así que la vulnerabilidad
  `CONFOUNDING` nunca se activa. El Codex reconstruye que la «exposición» real incluye
  variables de detectabilidad (sy_kepmag, MES/SNR, radio estelar) y por eso la confusión
  aparece. Ese es justo el hallazgo que mató la señal en los experimentos.
- **Supuestos por claim 3 → 7**, y **específicos** (p.ej. «permutar koi_smet dentro de
  bins de sy_kepmag preserva la estructura observacional necesaria para el nulo»), no un
  molde.
- **`content_distinctness` 0.33 → 1.0**: con Codex, las 6 hipótesis tienen contenido de
  vulnerabilidad **único**; ya no hay duplicados reales.

### Nota metodológica importante (auto-corrección)
`type_distinctness` **empeora** (0.167 → 0.0) con Codex, y eso es correcto: las hipótesis
rivales **comparten los TIPOS** de vulnerabilidad (todas son single-source, observacionales
con confusión, no replicadas) — lo que difiere es el **contenido**. Por eso el `type-set`
es un proxy engañoso de especificidad y el guard de de-duplicación se **cambió a comparar
contenido** (tipo + texto), no sólo tipos (`epistemic_bridge.run_epistemic`). Un módulo no
mejora por generar más texto; mejora porque **detecta la confusión, extrae supuestos
falsables por claim y no duplica contenido** — y en las tres el Codex path gana.

## Reproducir
```python
from acero.portal.eva_benchmark import compare
from acero.portal.epistemic_bridge import make_codex_extractor
compare(hyps, make_codex_extractor())   # hyps = store.list_objects(pid, kind="candidate")
```

**Veredicto:** `EVA_CORREGIDO_LISTO_PARA_BENCHMARK` → **cumplido**: el extractor Codex está
cableado (endpoint `/epistemic/questions` lo usa cuando Codex está disponible, con fallback
heurístico marcado), probado offline (mock) y medido en vivo. El fallback heurístico sigue
siendo honesto y trazable (procedencia + confianza).
