# ACERO — Publicación, réplica y validación externa

Cierra tres huecos: `EXTERNALLY_VALIDATED` no tenía motor, no había forma de que un
tercero verificara sin confiar en nosotros, y no se veía "¿qué me falta para publicar?".

## 1. Panel "¿Qué me falta para publicar?"
En el dashboard de cada investigación. Por dossier muestra el **nivel de madurez** y
un checklist con los bloqueadores reales:
afirmación central · contraevidencia/limitaciones · sin objeciones bloqueantes del
Revisor · reproducción computacional verificada · validación externa independiente ·
nivel = `READY_FOR_HUMAN_SCIENTIFIC_REVIEW` · **revisión humana aprobada** (esta
última ACERO no puede resolverla por ti — es el techo por diseño).
`GET /api/projects/{id}/publication` · `src/acero/portal/publication_status.py`

## 2. Exponer: paquete verificable offline
`POST /api/projects/{id}/publication/packet {experiment_id}` arma una carpeta (+zip)
autocontenida: `manifest.json` (cada archivo + sha256), los artefactos en `files/`,
`VERIFY.md`, `attestation.json` y **`verify.py` (solo stdlib)**. El revisor corre:

```bash
python verify.py     # INTACT | TAMPERED  — sin red, sin instalar, sin ACERO
```

Sigue siendo local-first: genera un **archivo que tú decides compartir**; ACERO no
publica solo. `src/acero/publication/verification_packet.py`

## 3. Validación externa que se gana
El revisor devuelve `attestation.json` →
`POST /api/projects/{id}/publication/attestation`. Reglas anti-farsa:
- El validador debe ser **humano** (rechaza `acero`, `ai`, `codex`, `claude`, `system`).
- **No puede ser el autor**; debe declarar independencia.
- Se **ata al hash del manifiesto**: si el contenido cambia después, la attestation
  queda **obsoleta** y deja de contar.
- Solo `reproduced` sube el nivel; `failed`/`partial` se **preservan** (la evidencia
  negativa también es evidencia).
- Con ≥ N validadores independientes (`ACERO_EXTERNAL_VALIDATIONS`, default 1),
  `externally_validated=True` alimenta `assess_readiness(...)`.
`src/acero/publication/external_validation.py`

## Flujo completo
```
dossier → panel muestra bloqueadores → generas paquete → lo compartes
   → tercero: python verify.py (INTACT) + reproduce → devuelve attestation
   → ACERO la registra → EXTERNALLY_VALIDATED → falta TU aprobación → exportar
```
Verificado en vivo: paquete (5 archivos, zip) → `INTACT` → attestation →
`externally_validated: True`; y `validator="ACERO"` → **HTTP 422**.

Tests: `tests/unit/test_external_validation.py` (13).
