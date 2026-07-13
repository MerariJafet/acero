"""ACERO command-line interface.

Commands:
  acero doctor         environment + policy health check
  acero policy check   load and validate all policies
  acero project init   create a research project
  acero project list   list projects
  acero project export  export a dossier (JSON + Markdown + hashes)
  acero pilot run      run the Sprint-4 computational pilot end to end
  acero serve          run the API
  acero test           run the test suite
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import typer

from .. import __version__
from ..core.config import get_config, repo_root
from ..core.logging import configure_logging
from ..ledger.db import default_session_factory
from ..ledger.export import export_project
from ..ledger.service import ResearchLedger
from ..policies.guard import PolicyGuard
from ..policies.loader import load_policies

app = typer.Typer(help="ACERO — Adaptive Computational Engine for Research and Epistemic Reasoning", no_args_is_help=True)
project_app = typer.Typer(help="Manage research projects")
app.add_typer(project_app, name="project")


def _ledger() -> ResearchLedger:
    return ResearchLedger(default_session_factory())


@app.command()
def doctor() -> None:
    """Report environment + policy health. Exits non-zero if anything is broken."""
    configure_logging(json=False)
    ok = True
    typer.echo(f"ACERO v{__version__}")
    typer.echo(f"Python: {sys.version.split()[0]}")
    typer.echo(f"Repo root: {repo_root()}")

    cfg = get_config()
    typer.echo(f"Env: {cfg.app.env} · DB: {cfg.abs_db_url()}")
    typer.echo(f"LLM provider: {cfg.llm.provider} · Sandbox: {cfg.sandbox.backend}")

    try:
        bundle = load_policies()
        typer.echo(f"Policies loaded: {', '.join(sorted(bundle.policies))} ✓")
    except Exception as exc:  # noqa: BLE001
        ok = False
        typer.echo(f"Policies: FAILED — {exc}")

    guard = PolicyGuard()
    paid = guard.paid_llm_allowed()
    typer.echo(f"Paid services enabled: {paid} (expected: False)")
    if paid:
        ok = False
        typer.echo("  WARNING: paid services are enabled — unexpected for local-first default.")

    for tool in ("docker", "ollama", "git"):
        typer.echo(f"{tool}: {'found' if shutil.which(tool) else 'not found'}")

    typer.echo("OK ✓" if ok else "PROBLEMS FOUND ✗")
    raise typer.Exit(code=0 if ok else 1)


@app.command("policy")
def policy_check() -> None:
    """Load and validate all policy files."""
    bundle = load_policies()
    for name in sorted(bundle.policies):
        typer.echo(f"  {name}: v{bundle.policies[name].get('version')} ✓")
    typer.echo("All policies valid ✓")


@project_app.command("init")
def project_init(
    title: str = typer.Argument(..., help="Project title"),
    domain: str = typer.Option("general", help="Scientific domain"),
    description: str = typer.Option("", help="Short description"),
) -> None:
    """Create a new research project."""
    led = _ledger()
    proj = led.create_project(title, description=description, domain=domain)
    typer.echo(f"Created project {proj.id}: {proj.title} [{proj.domain}]")


@project_app.command("list")
def project_list() -> None:
    """List research projects."""
    led = _ledger()
    projs = led.list_projects()
    if not projs:
        typer.echo("(no projects)")
        return
    for p in projs:
        typer.echo(f"  {p.id}  {p.title}  [{p.domain}]  {p.state.value}")


@project_app.command("export")
def project_export(
    project_id: str = typer.Argument(...),
    out: str = typer.Option("", help="Output directory (default: research/artifacts/<id>_export)"),
) -> None:
    """Export a complete, hashed dossier for a project."""
    led = _ledger()
    guard = PolicyGuard()
    guard.check_publication(human_reviewed=True)  # local export is human-invoked
    out_dir = out or str(repo_root() / "research" / "artifacts" / f"{project_id}_export")
    paths = export_project(led, project_id, out_dir)
    typer.echo(f"Dossier exported to {paths['dir']}")
    for k in ("json", "markdown", "manifest"):
        typer.echo(f"  {k}: {paths[k]}")


@app.command("pilot")
def pilot_run(
    title: str = typer.Option("ACERO cooling-law pilot", help="Project title"),
    seeds: str = typer.Option("1,2,3", help="Comma-separated seeds"),
) -> None:
    """Run the Sprint-4 computational research pilot end to end."""
    from ..experiment.orchestrator import run_pilot

    led = _ledger()
    proj = led.create_project(title, domain="physics",
                              description="Symbolic-discovery pilot on synthetic cooling data.")
    seed_list = [int(s) for s in seeds.split(",") if s.strip()]
    art = repo_root() / "research" / "artifacts" / f"{proj.id}_pilot"
    rep = run_pilot(led, proj.id, artifacts_root=art, seeds=seed_list)
    typer.echo(f"Project {proj.id}")
    typer.echo(f"Best model: {rep['overall_best_model']} {rep['best_counts']}")
    typer.echo(f"Recovered k={rep['mean_recovered_k']:.4f} (true {rep['true_k']})")
    typer.echo(f"Reproduced: {rep['reproduced']}")
    typer.echo(f"Skeptic: {rep['skeptic']['n_objections']} objections, "
               f"{rep['skeptic']['n_failed_checks']} failed checks")
    typer.echo(f"Artifacts: {art}")
    typer.echo("NOTE: recovering a known law is NOT a discovery.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the ACERO API."""
    import uvicorn

    uvicorn.run("acero.api.app:create_app", host=host, port=port, factory=True)


@app.command()
def test() -> None:
    """Run the test suite (pytest)."""
    root = repo_root()
    code = subprocess.call([sys.executable, "-m", "pytest", str(root / "tests")], cwd=str(root))
    raise typer.Exit(code=code)


@app.command()
def version() -> None:
    """Print the ACERO version."""
    typer.echo(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
