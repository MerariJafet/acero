# ACERO 2.0.0-rc2 — Security Review

Hereda todos los controles de RC1 (ver `ACERO_V2_RC1_SECURITY.md`): sandbox restringido, gate
in-line universal con tokens de mutación single-use, secreto HMAC desde entorno, portal
local-first con CSP, publicación automática prohibida, datasets gated.

## Superficie nueva (Sprints 18/19)
- **Self-evaluation:** solo lectura + escritura de baselines firmados; los baselines detectan
  modificación silenciosa (firma + hash). No ejecuta código no confiable. Prompts se evalúan
  contra fixtures offline; respuestas inseguras/sobreafirmantes FALLAN.
- **Collaboration:** los bundles se escriben **solo local**; **nada se envía**. Los reviews
  importados **nunca se auto-confían** y se validan por schema + version binding. Los borradores
  de comunicación tienen `sent: False`. Las licencias desconocidas/incompatibles **bloquean** el
  bundle. La IA no puede aprobar respuestas ni figurar como autora.

## Hallazgos críticos
Ninguno conocido. Riesgos abiertos documentados en el threat model.
