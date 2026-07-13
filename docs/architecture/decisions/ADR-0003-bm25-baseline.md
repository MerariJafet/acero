# ADR-0003: BM25 léxico como línea base de recuperación

- **Estado:** Aceptado
- **Fecha:** 2026-07-12

## Contexto
El Sprint 3 pide recuperación con procedencia sin servicios de pago. La búsqueda
semántica requiere un modelo de embeddings local (p. ej. vía Ollama), que en esta
sesión no está sirviendo. La misión prohíbe declarar superioridad de un método
sin benchmark.

## Decisión
Implementar **BM25** (Okapi, k1=1.5, b=0.75) en Python puro como línea base sólida
y honesta. La recuperación semántica/híbrida queda como extensión documentada,
detrás de una interfaz de método (`retrieval.method: bm25 | vector | hybrid`), a
activar cuando exista un modelo de embeddings local y un benchmark que la respalde.

## Consecuencias
- (+) Cero dependencias externas, cero costo, totalmente reproducible.
- (+) Cada resultado porta procedencia (documento, sección, span de caracteres, hash).
- (−) BM25 no capta sinonimia/semántica; se mide con `evaluation/retrieval_metrics`
  (recall@k, precision@k, MRR) sobre un corpus de prueba etiquetado.
