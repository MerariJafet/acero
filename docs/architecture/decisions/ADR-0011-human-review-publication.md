# ADR-0011: Human Scientific Review & Local Publication Preparation

- **Estado:** Aceptado
- **Fecha:** 2026-07-14

## Contexto
Sprint 12 (cierre del roadmap) debe permitir preparar un artefacto para revisión humana y
export LOCAL, sin publicación automática, respetando la constitución (regla 11) y el techo
de readiness del Sprint 11.

## Decisión
`src/acero/publication/` (dossier, review, export, engine): expediente revisable +
sign-off humano estructurado + export gated local. La aprobación exige reconocimientos,
comprensión y razón; ata al contenido por hash; un revisor IA no puede aprobar. El export
verifica política + readiness + comprensión + gate + contradicciones + aprobación vinculante.

## Alternativas descartadas
- Un estado `APPROVE_FOR_PUBLICATION` o publicación automática (rechazado por constitución).
- Aprobación por checkbox sin razón ni binding (rechazado tras auditoría Codex).
- Export sin verificar readiness/comprensión (rechazado).

## Consecuencias
- (+) 6/6 casos del gauntlet; export aprobado nunca auto-publica; aprobación atada al
  contenido.
- (−) "comprensión suficiente" depende del gate de comprensión; el export no revierte
  efectos externos — declarado.
