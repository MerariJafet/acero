# ACERO — Hipatia fuerte (checador de novedad multi-fuente)

> "Hagamos al más débil el más fuerte: pongamos el esfuerzo en Hipatia — la novedad casi
> siempre daba 'uncertain'; sin ella no sabemos si algo es contribución real." — Merari

## Por qué era débil

La versión previa hacía **una** búsqueda con la **frase completa** de la conjetura como
query, contra **una** fuente (OpenAlex). Una conjetura precisa ("para todo grafo con
6≤n≤14…") es una pésima consulta académica → casi nada relevante → el juez se encogía de
hombros: `uncertain`. Inútil.

## Cómo es fuerte ahora

1. **Redacción de consultas (Hipatia bibliotecaria):** un LLM convierte la afirmación en
   **3-5 consultas académicas concisas** con los nombres canónicos de los objetos/teoremas
   y sinónimos — como buscaría un experto —, no la frase literal ni los rangos numéricos.
2. **Multi-fuente en paralelo:** **OpenAlex + arXiv + Crossref** (todas gratis, sin key),
   fusionadas y deduplicadas por DOI/título.
3. **Juez que clasifica:** lee los papers reales y decide `already_resolved` /
   `likely_open` / `uncertain`, con **confianza**, separando *resolving_papers* (los que
   resuelven) de *related_papers* (relacionados). Se le instruye a **reservar 'uncertain'
   solo para ausencia real de señal**; con búsqueda amplia, decide.
4. **Regla dura:** si aparece un paper que **resuelve** → `already_resolved` (aunque el
   juez dude). Un *recovery* nunca se disfraza de descubrimiento.

## Honestidad (sin cambios)

- "No encontrado" **no** prueba novedad → techo `likely_open`, nunca `novel`.
- Sin cobertura real de búsqueda → `uncertain`, jamás luz verde.

## Salida

`{verdict, recovery_risk, confidence, resolving_papers[], related_papers[], queries[],
sources[], hits[], rationale, recommendation, searched}` — compatible con el panel y con
quien la llama (explorador, probador, research loop).

## Archivos

- `src/acero/discovery/novelty_check.py` — `NoveltyChecker`, `multi_source_search`,
  `openalex_search` / `arxiv_search` / `crossref_search`, query-craft + judge.
- `tests/unit/test_novelty_check.py` — 8 tests offline (searcher/provider/query-gen inyectables).
