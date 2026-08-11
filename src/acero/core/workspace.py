"""EL ESPACIO DE TRABAJO — separa el programa de lo que el programa produce.

Decisión de Merari (2026-08-11): el repositorio debe contener SOLO el motor, de
modo que cualquiera pueda instalarlo y usarlo para SUS investigaciones. Todo lo
que una corrida genera —investigaciones, aprendizaje, datos, resultados— vive
fuera, en un espacio de trabajo propio del usuario.

Antes de esto los datos ya estaban fuera de git, pero **físicamente dentro de la
carpeta del programa** (`repo_root()/"acero_data"`, `research/artifacts`). Eso
mezcla dos cosas con ciclos de vida distintos: el código se actualiza y se
comparte; los resultados se acumulan y son privados. Y hace que borrar o reclonar
el repo se lleve por delante meses de trabajo.

RESOLUCIÓN (en este orden, la primera que exista manda):
  1. la variable de entorno ACERO_HOME — control explícito, gana siempre;
  2. ~/ACERO — el valor por defecto, igual para cualquiera que instale.

No se usa una ruta relativa al repositorio a propósito: dos clones distintos del
programa deben poder compartir el mismo espacio de trabajo, y mover el repo no
debe perder los datos.

CONECTORES: `ensure_workspace()` crea el árbol la primera vez que se necesita y
deja un LEEME.md explicando qué va en cada sitio. Se invoca desde el arranque del
portal y del CLI, así que instalar y correr basta — el usuario no configura nada.
"""

from __future__ import annotations

import os
from pathlib import Path

# Las carpetas del espacio de trabajo y qué significa cada una. El texto va al
# LEEME.md para que alguien que abra la carpeta a los seis meses entienda qué
# está mirando sin volver al código.
SUBDIRS: dict[str, str] = {
    "investigaciones": "Una carpeta por investigación: hipótesis, experimentos, "
                       "resultados y dossier. Es lo que produce el Consejo.",
    "aprendizaje": "Modo Aprender: árboles de conceptos, cursos generados y "
                   "progreso.",
    "datos": "Estado del programa: base del ledger, sesiones del portal, "
             "catálogos y cachés. No editar a mano.",
    "resultados": "Artefactos de experimentos: scripts ejecutados, salidas, "
                  "figuras y certificados de reproducción.",
    "literatura": "Papers descargados y fichas de novedad (Hipatia).",
    "exportes": "Paquetes listos para compartir o publicar hacia afuera.",
}

_LEEME = """# Espacio de trabajo de ACERO

Esta carpeta es **tuya**: contiene lo que ACERO produce, no el programa.
Puedes moverla, respaldarla o borrarla sin tocar la instalación — y puedes
reinstalar o actualizar el programa sin perder nada de aquí.

Para cambiarla de sitio, define la variable de entorno `ACERO_HOME` apuntando a
la ruta nueva y mueve la carpeta.

## Qué hay en cada sitio

{secciones}

---
Creado automáticamente por ACERO. Este archivo se regenera si lo borras.
"""


def workspace() -> Path:
    """La raíz del espacio de trabajo. No crea nada — solo resuelve."""
    env = os.environ.get("ACERO_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "ACERO"


def ensure_workspace() -> Path:
    """Crea el árbol si falta y devuelve la raíz. Idempotente y barata.

    Escribir el LEEME en cada llamada es deliberado: si el usuario lo borra o si
    añadimos una carpeta nueva, la explicación vuelve sola y no queda una carpeta
    huérfana sin decir qué es."""
    root = workspace()
    root.mkdir(parents=True, exist_ok=True)
    for nombre in SUBDIRS:
        (root / nombre).mkdir(exist_ok=True)
    secciones = "\n".join(f"- **{n}/** — {d}" for n, d in SUBDIRS.items())
    (root / "LEEME.md").write_text(_LEEME.format(secciones=secciones),
                                   encoding="utf-8")
    return root


def wpath(*partes: str) -> Path:
    """Ruta dentro del espacio de trabajo, con el árbol garantizado.

    Es el punto único que debe usar el resto del programa: `wpath("datos",
    "acero.sqlite")`. Nadie más debería calcular rutas de datos a mano — esa
    dispersión fue justo lo que dejó los datos dentro del repo."""
    root = ensure_workspace()
    destino = root.joinpath(*partes)
    if destino.suffix:
        destino.parent.mkdir(parents=True, exist_ok=True)
    else:
        destino.mkdir(parents=True, exist_ok=True)
    return destino


_AVISADO: set[str] = set()


def data_path(rel: str, *, legacy: Path | None = None) -> Path:
    """Ruta de datos con TRANSICIÓN segura desde instalaciones viejas.

    El problema real: si el código empieza a mirar el espacio de trabajo de
    golpe, una instalación que aún tiene sus datos dentro del programa arrancaría
    con la base VACÍA — y eso, sobre una investigación en curso, parece pérdida
    total. Así que mientras exista el sitio viejo se sigue usando, pero se avisa
    por consola en cada arranque hasta que se migre. Fallback sí; silencioso no.
    """
    nueva = workspace() / rel
    if legacy is not None and legacy.exists() and not nueva.exists():
        if rel not in _AVISADO:
            _AVISADO.add(rel)
            print(f"[ACERO] usando datos heredados en {legacy} — "
                  f"ejecuta `acero workspace migrar` para moverlos a {nueva}",
                  flush=True)
        return legacy
    return nueva


def legacy_dirs(repo: Path) -> list[Path]:
    """Carpetas de la época en que los datos vivían dentro del programa.

    Se listan para que la migración sepa qué mover y para poder AVISAR si alguien
    actualiza el programa y todavía tiene datos ahí. No se leen en silencio: un
    fallback automático haría que la mitad del estado viviera en cada sitio sin
    que nadie se entere."""
    return [d for d in (repo / "acero_data", repo / "research") if d.exists()]
