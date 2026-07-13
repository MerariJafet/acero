# Sprint 3 — Biblioteca científica y procedencia · Reporte

**Estado:** ✅ Terminado (baseline léxico; semántico documentado como extensión)

## Entregables
- **Interfaz de fuentes** (`literature/sources.py`): adaptador arXiv como
  *interfaz con guarda* (deshabilitado por `data_access.yaml`, requiere
  aprobación humana; probado por diseño, sin red).
- **Ingestión de documentos locales** (`.txt`/`.md`; `.pdf` con backend opcional
  `pypdf`): checksum → metadatos → secciones → fragmentos → índice → procedencia.
- **Chunking con referencias** (`documents.chunk_text`): spans de caracteres,
  sección, hash y versión de parser por fragmento.
- **Recuperación léxica BM25** (Okapi, `retrieval.py`) en Python puro — cada hit
  porta procedencia (documento, sección, span, hash).
- **Verificación de citas** (`citations.py`): rechaza referencias inexistentes y
  fragmentos que no pertenecen al documento; **detección de duplicados** por checksum.
- **Registro de licencia y tipo de publicación** en `SourceDocument`.
- **Almacén** (`literature/store.py`) + reconstrucción de índice.
- **Métricas de recuperación** (`evaluation/retrieval_metrics.py`): recall@k,
  precision@k, MRR.
- **Corpus de prueba** (`tests/fixtures/corpus/`) con set de consultas etiquetadas.

## Métricas de recuperación (corpus de prueba, k=3)
| Métrica | Valor |
|---|---|
| Fragmentos indexados | 4 |
| Consultas | 4 |
| Recall@3 | 0.875 |
| Precision@3 | 0.583 |
| MRR | 1.00 |
| Documento correcto en top-1 | 4/4 |

> Corpus deliberadamente pequeño para pruebas rápidas; los números crecen en
> significancia con corpus mayores. No se afirma superioridad de ningún método
> sin benchmark (ver ADR-0003).

## Criterios de aceptación
| Criterio | Evidencia |
|---|---|
| Ingerir un PDF/documento local | `test_ingest_local_document` |
| Recuperar fragmento con ubicación | `test_retrieval_returns_provenance` |
| Toda respuesta con procedencia | provenance en cada `RetrievalHit` |
| Referencia inexistente se rechaza | `test_citation_verifier_rejects_fabricated` |
| Duplicados detectados | `test_duplicate_detection` |
| Funciona sin API de pago | BM25 puro, sin red |
| Medición de precisión de recuperación | `test_retrieval_metrics` + tabla arriba |

## Pendientes / deuda
- Recuperación **semántica/híbrida** (necesita modelo de embeddings local, p. ej.
  Ollama) + benchmark comparativo BM25 vs vector vs híbrido.
- Conectores arXiv/Crossref/OpenAlex reales con límites de tasa (tras aprobación).
- Extracción de PDF robusta (hoy opcional vía `pypdf`).
