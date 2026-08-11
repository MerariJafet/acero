# El programa y tu trabajo viven separados

ACERO se instala una vez y se actualiza muchas. Tus investigaciones, en cambio,
se acumulan durante meses y son tuyas. Por eso viven en sitios distintos.

```
  El programa                      Tu espacio de trabajo
  (este repositorio)               (~/ACERO, o donde digas)
  ├── src/        el motor         ├── investigaciones/   lo que produce el Consejo
  ├── tests/                       ├── aprendizaje/       árboles y cursos
  ├── docs/       cómo funciona    ├── datos/             ledger, sesiones, cachés
  └── scripts/                     ├── resultados/        experimentos y figuras
                                   ├── literatura/        papers y fichas de novedad
                                   └── exportes/          paquetes para compartir
```

Puedes borrar y reclonar el repositorio sin perder nada de tu trabajo, y puedes
respaldar o mover tu trabajo sin tocar la instalación.

## Dónde está

Por defecto **`~/ACERO`**. Es la misma ruta para cualquiera que instale el
programa, sin depender de dónde clonó el repositorio — y así dos copias del
programa pueden compartir el mismo espacio de trabajo.

Para cambiarla, define `ACERO_HOME`:

```bash
export ACERO_HOME=/media/disco-grande/ACERO
```

La carpeta se crea sola la primera vez que hace falta, con un `LEEME.md` dentro
que explica para qué es cada subcarpeta. No hay que configurar nada.

## Comandos

```bash
acero workspace estado             # dónde está y qué contiene
acero workspace crear              # prepara el árbol (idempotente)
acero workspace migrar --dry-run   # plan de migración, sin tocar disco
acero workspace migrar             # mueve de verdad
```

## Si vienes de una versión anterior

Hasta agosto de 2026 los datos vivían **dentro** de la carpeta del programa
(`acero_data/`, `research/artifacts/`). Seguían fuera de git, pero físicamente
dentro: reclonar o mover el repositorio se llevaba el trabajo por delante.

El programa detecta esa situación y **sigue usando el sitio viejo**, avisando en
cada arranque:

```
[ACERO] usando datos heredados en …/acero_data/portal_sessions.json —
        ejecuta `acero workspace migrar` para moverlos a ~/ACERO/datos/…
```

No cambia nada solo, a propósito: arrancar de golpe contra un espacio de trabajo
vacío parece pérdida total cuando en realidad los datos siguen ahí.

Para migrar:

1. **Para el portal y cualquier cómputo largo.** La migración se niega a correr
   con la base abierta (lo detecta por el `-wal` de SQLite) o con un cómputo en
   marcha: mover en caliente parte el estado en dos.
2. `acero workspace migrar --dry-run` y revisa el plan. Puede haber decenas de
   GB en `research/artifacts`.
3. `acero workspace migrar`.

Si algún destino ya existe con contenido, ese paso se marca **en conflicto** y se
omite. Nunca se machaca nada: preferimos una migración a medias y declarada.

## Qué se queda en el repositorio

Todo lo que es motor. Incluido `research/TOOLBOX.md` (el catálogo LEGO de piezas
que el Consejo puede componer) y `research/templates/`, que son activos del
programa aunque vivan bajo `research/`.

Lo que sale: la base del ledger, las sesiones, los artefactos de experimentos,
las cachés, los datasets descargados y las investigaciones concretas.
