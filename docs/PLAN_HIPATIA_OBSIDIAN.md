# PLAN — Hipatia → Obsidian con embeddings (GPU)

**Idea de Merari:** cuando Hipatia descargue literatura (arXiv, etc.), que la
vuelque a su bóveda de Obsidian como notas + tablas de embeddings, para que el
conocimiento quede navegable y enlazado donde él ya piensa (MAGNO-Brain).

## Aclaración técnica primero (honesta)

**Obsidian NO corre con CUDA** — es un editor de markdown (Electron); no computa
nada pesado. Lo que SÍ corre con CUDA es el **modelo de embeddings** que convierte
cada paper/nota en un vector. La arquitectura correcta es:

```
Hipatia (novelty_check) descarga metadatos/abstract/PDF
        │
        ▼
  NOTA MARKDOWN → bóveda Obsidian (~/Documents/MAGNO-Brain/ACERO-Lit/)
  (título, autores, año, abstract, veredicto de novedad, enlaces [[wiki]],
   frontmatter YAML con arxiv_id, proyecto, hipótesis relacionada)
        │
        ▼
  EMBEDDING del texto (sentence-transformers, GPU cuando esté activa;
  CPU de respaldo — mismo modelo, solo más lento)
        │
        ▼
  ÍNDICE VECTORIAL local (sqlite + numpy/faiss) junto a la bóveda
        │
        ▼
  BÚSQUEDA SEMÁNTICA: Hipatia consulta "¿ya se hizo esto?" por SIGNIFICADO,
  no por palabras clave — y el dashboard puede mostrar vecinos de cada nota
```

Obsidian solo LEE las notas (gratis: grafo de enlaces nativo). El índice vectorial
vive al lado y lo usa ACERO.

## Qué gana ACERO

1. **Hipatia más fuerte:** hoy busca por keywords; con embeddings detecta trabajos
   equivalentes con OTRA terminología (el modo de fallo real del "Erdősgate").
2. **Memoria de literatura acumulativa:** cada investigación deja notas enlazadas
   a sus hipótesis — la biblioteca crece con el sistema.
3. **Primer uso real de la GPU** con tensores de verdad (miles de embeddings por
   lote) — el caso perfecto para estrenar el protocolo.

## Fases (LIT-1 … LIT-4)

| Fase | Qué | GPU |
|---|---|---|
| LIT-1 | `integrations/obsidian.py`: escribir notas markdown con frontmatter a la bóveda (ruta configurable, sin borrar nada existente jamás) | no |
| LIT-2 | Motor de embeddings `science/embeddings.py`: sentence-transformers multilingüe, lote, con `gpu.wait_for_vram()` y fallback CPU | **sí** |
| LIT-3 | Índice vectorial (sqlite+numpy; faiss si hace falta) + API de vecinos | opcional |
| LIT-4 | Cablear a Hipatia: cada `literature` del ledger → nota + vector; `novelty_check` consulta el índice ANTES de ir a la red | — |

## Protocolo GPU (innegociable, ya en el TOOLBOX)

Antes de arrancar LIT-2 con CUDA: **avisar a Merari y esperar su confirmación** —
debe instalar `nvidia-utils` y **reiniciar la PC**. Mientras tanto LIT-1/LIT-3/LIT-4
funcionan en CPU (más lento pero idéntico resultado). Regla del 90% de VRAM en
todo momento (`gpu.wait_for_vram()`).

## Nota sobre la bóveda

MAGNO-Brain ya tiene un servidor de memoria propio (heyra). ACERO escribirá SOLO
en su subcarpeta (`ACERO-Lit/`) y jamás tocará notas ajenas. La ruta será
configurable en `configs/default.yaml`.
