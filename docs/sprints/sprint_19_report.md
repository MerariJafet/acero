# Sprint 19 — Collaboration & External Review Preparation · Report

**Estado:** ✅ Terminado · **Rama:** `feature/acero-v2-rc2-sprints-18-19`

## Qué se construyó (`src/acero/collaboration/`)
PREPARA el trabajo de ACERO para que científicos humanos externos lo revisen, cuestionen y
reproduzcan — **sin contactar a nadie, sin enviar nada, sin crear cuentas, sin publicar.**

- **CollaborationWorkspace** (`engine.py`) con roles de revisor (no identidades inventadas),
  preguntas de revisión, licencia y estado; **borradores de comunicación** (review/dataset/
  reproducibility/mentorship/validation) que **nunca se envían** (`sent: False`) e incluyen uso
  de IA y "esto es preparación, no validación".
- **External Review Bundle** (`bundle.py`): genera localmente el paquete completo (README,
  executive_summary, central_claims, methods, evidence_map, counterevidence, limitations,
  reliability_card, review_questions, reviewer_form, AI_USE, LICENSE, checksums,
  version_binding) con **fingerprint de versión** (commit + hashes). **Bloquea** si una
  licencia es incompatible/desconocida. Blind export (OPEN/PARTIALLY/BLINDED) que **conserva**
  la información de reproducibilidad.
- **Import estructurado** (`review_import.py`): valida schema, **nunca auto-confía**
  (`trusted=False`), y exige **version binding** — una revisión de otra versión/hash NO aplica.
- **Issue Tracker** (`issues.py`): convierte revisiones en issues rastreables (OPEN…RESOLVED/
  REQUIRES_EXTERNAL_VALIDATION); un issue crítico permanece sin resolver hasta cambiarlo.
- **Response drafts** (`responses.py`): Codex puede redactar; **un humano (no IA) debe
  aprobar** antes de usar.
- **External Validation Plan** (`engine.py`): plan por claim; **un plan NO es validación**
  (nada se ejecuta; blockers presentes).
- **Authorship CRediT** (`models.py`): matriz de 9 roles; **IA nunca figura como autora**;
  asistencia de IA se registra por separado.
- **Licensing** (`licensing.py`): desconocido/incompatible = **bloqueado** (humano resuelve).
- **Portal:** sección **Collaboration**. **CLI:** `acero collab bundle/questions/gauntlet`.

## Benchmark
External Review Preparation Gauntlet: **11/11** — bundle preparado; review de versión correcta
(no auto-confiada) vs incorrecta (bloqueada); bundle alterado (bloqueado); reviewer inválido;
comentario sin claim (rechazado); issue crítico rastreado; licencia incompatible/desconocida
(bloqueada); autoría IA (imposible); respuesta no aprobada (IA no puede aprobar).

## Calidad
**698 pruebas en verde** (+22), ruff limpio, mypy limpio (295 archivos), `make verify` OK.
3 schemas nuevos (workspace, external_review, review_issue).

## Honestidad
Un review bundle **NO** es revisión externa. Importar un review **NO** legitima al revisor. Un
plan de validación **NO** es validación. Nada se envía ni se contacta.
