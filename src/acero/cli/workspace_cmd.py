"""`acero workspace` — ver y mover el espacio de trabajo.

El conector que le faltaba al programa: quien lo instala no debería tener que
saber dónde van los datos. `estado` lo dice, `crear` lo prepara y `migrar` saca
lo que quedó dentro de la carpeta del programa en versiones anteriores.
"""

from __future__ import annotations

import typer

from ..core.config import repo_root
from ..core.migrate_workspace import apply, plan
from ..core.workspace import SUBDIRS, ensure_workspace, legacy_dirs, workspace

workspace_app = typer.Typer(help="Espacio de trabajo: dónde viven tus "
                                 "investigaciones, datos y resultados",
                            no_args_is_help=True)


@workspace_app.command("estado")
def estado() -> None:
    """Dónde está el espacio de trabajo y qué contiene."""
    raiz = workspace()
    typer.echo(f"Espacio de trabajo: {raiz}")
    typer.echo(f"  existe: {'sí' if raiz.exists() else 'no (se crea al primer uso)'}")
    if raiz.exists():
        for nombre, desc in SUBDIRS.items():
            d = raiz / nombre
            n = sum(1 for _ in d.iterdir()) if d.is_dir() else 0
            typer.echo(f"  {nombre:<16} {n:>4} entradas — {desc[:60]}")
    viejas = legacy_dirs(repo_root())
    if viejas:
        typer.echo("\n⚠️  Todavía hay datos DENTRO de la carpeta del programa:")
        for d in viejas:
            typer.echo(f"     {d}")
        typer.echo("   Ejecuta `acero workspace migrar --dry-run` para ver el plan.")


@workspace_app.command("crear")
def crear() -> None:
    """Crea el árbol del espacio de trabajo (idempotente)."""
    raiz = ensure_workspace()
    typer.echo(f"Listo: {raiz}")


@workspace_app.command("migrar")
def migrar(
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="solo mostrar el plan, no mover nada"),
    forzar: bool = typer.Option(False, "--forzar",
                                help="ignorar bloqueos (solo si sabes que el "
                                     "portal está parado y el WAL es huérfano)"),
) -> None:
    """Mueve datos y resultados fuera de la carpeta del programa.

    Con --dry-run no toca disco. Sin él, se niega a correr si el portal tiene la
    base abierta o si hay un cómputo largo en marcha: mover en caliente parte el
    estado en dos."""
    pl = plan(repo_root())
    typer.echo(pl.resumen())
    if dry_run:
        typer.echo("\n(--dry-run: no se movió nada)")
        raise typer.Exit(0)
    if pl.bloqueos and not forzar:
        typer.echo("\nNo se movió nada. Para el portal y vuelve a intentar.")
        raise typer.Exit(1)
    movidos = apply(pl, forzar=forzar)
    typer.echo(f"\nMovidos {len(movidos)} elementos a {workspace()}")
