# ACERO 2.0.0-rc1 — Security Review

## Superficie y controles
- **Sandbox:** ejecución de código en sandbox restringido (subprocess por defecto; Docker
  `--network=none --read-only --cap-drop=ALL` opcional). Sin red, sin secretos, límites de
  recursos, timeout, screening estático.
- **Gate in-line universal:** toda mutación científica central requiere contexto (contextvars,
  async-safe) + token de mutación single-use (HMAC, TTL, replay/tamper-proof). Test de
  arquitectura falla si un módulo no-boundary importa persistencia directamente.
- **Secretos:** secreto HMAC desde entorno (`ACERO_HMAC_SECRET`), key id, rotación; nunca en
  Git; production rehúsa firmar sin secreto; nunca se muestra completo.
- **Portal:** local-first; CSP estricta, X-Frame-Options DENY, nosniff; static seguro (sin path
  traversal); sin secretos/tokens/shell expuestos; sin `eval`.
- **Publicación:** automática **prohibida** por política; export solo local con revisión humana
  vinculante (hash de contenido, revisor no-IA).
- **Datasets:** públicos, gated (`authorized=True`), hasheados, gitignored; sin credenciales;
  sin costo; <500 MB.
- **Costos:** servicios de pago desactivados por defecto + circuit breaker.

## Hallazgos críticos
Ninguno conocido. Riesgos abiertos documentados en el threat model
(`docs/security/threat_model.md`): sandbox de subproceso más débil que contenedor para código
NO confiable de terceros; secreto de token por-proceso; concurrencia multiproceso no ejercida
en unit tests.
