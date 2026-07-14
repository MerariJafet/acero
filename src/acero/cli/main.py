"""ACERO command-line interface.

Commands:
  acero doctor         environment + policy health check
  acero policy check   load and validate all policies
  acero project init   create a research project
  acero project list   list projects
  acero project export  export a dossier (JSON + Markdown + hashes)
  acero domain list    list scientific domain plugins
  acero domain benchmark  run known-answer domain benchmarks
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
domain_app = typer.Typer(help="Scientific domain plugins")
hypothesis_app = typer.Typer(help="Discovery Engine: hypotheses")
experiment_app = typer.Typer(help="Discovery Engine: experiments")
discovery_app = typer.Typer(help="Discovery Engine: status / next / report")
benchmark_app = typer.Typer(help="Validation benchmarks")
world_app = typer.Typer(help="World Model Engine: living epistemic graph")
app.add_typer(project_app, name="project")
app.add_typer(domain_app, name="domain")
app.add_typer(hypothesis_app, name="hypothesis")
app.add_typer(experiment_app, name="experiment")
app.add_typer(discovery_app, name="discovery")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(world_app, name="world")


def _ledger() -> ResearchLedger:
    return ResearchLedger(default_session_factory())


def _discovery():
    """Return (session_factory, ledger, store) bound to the same DB."""
    from ..discovery.store import DiscoveryStore

    sf = default_session_factory()
    led = ResearchLedger(sf)
    return sf, led, DiscoveryStore(sf, led)


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

    for tool in ("docker", "codex", "ollama", "git"):
        typer.echo(f"{tool}: {'found' if shutil.which(tool) else 'not found'}")

    # Sandbox backend readiness
    try:
        from ..sandbox.docker_runner import docker_available, image_present
        if cfg.sandbox.backend == "docker":
            ready = docker_available() and image_present()
            typer.echo(f"docker sandbox image ready: {ready}")
            if not ready:
                typer.echo("  build it with: infra/sandbox/build.sh")
    except Exception:  # noqa: BLE001
        pass

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


@domain_app.command("list")
def domain_list() -> None:
    """List available scientific domain plugins."""
    from ..domains.registry import all_plugins

    for p in all_plugins():
        typer.echo(f"  {p.name}: tools={', '.join(p.allowed_tools)}")


@domain_app.command("info")
def domain_info(name: str = typer.Argument(...)) -> None:
    """Show a domain plugin's units, tools, simulators, and risks."""
    import json as _json

    from ..domains.registry import get_plugin

    typer.echo(_json.dumps(get_plugin(name).info(), indent=2, ensure_ascii=False))


@domain_app.command("benchmark")
def domain_benchmark(
    name: str = typer.Option("", help="Domain name, or empty for all"),
) -> None:
    """Run known-answer benchmarks for one or all domains."""
    from ..domains.registry import get_plugin, run_all_benchmarks

    results = {name: get_plugin(name).benchmark().to_dict()} if name else run_all_benchmarks()
    ok = True
    for dname, r in results.items():
        mark = "✓" if r["all_passed"] else "✗"
        typer.echo(f"  {dname}: {r['passed']}/{r['total']} {mark}")
        ok = ok and r["all_passed"]
    typer.echo("All domain benchmarks passed ✓" if ok else "SOME BENCHMARKS FAILED ✗")
    raise typer.Exit(code=0 if ok else 1)


def _load_candidates(store, project_id: str):
    from ..discovery.candidates import HypothesisCandidate
    return [HypothesisCandidate(**p)
            for p in store.list_objects(project_id, kind="candidate")]


@hypothesis_app.command("generate")
def hypothesis_generate(
    project_id: str = typer.Argument(...),
    n: int = typer.Option(8, help="Number of hypotheses"),
    llm: bool = typer.Option(False, "--llm", help="Use Codex to generate"),
    question: str = typer.Option("What model explains the observed data?", help="Research question"),
) -> None:
    """Generate competing hypothesis candidates for a project."""
    from ..core.ids import new_id
    from ..discovery.supervisor import DiscoverySupervisor
    from ..epistemology.schemas import ResearchQuestion
    from ..llm.providers import get_provider

    sf, led, store = _discovery()
    if led.get_project(project_id) is None:
        typer.echo(f"project {project_id} not found")
        raise typer.Exit(1)
    q = led.add_entity(ResearchQuestion(id=new_id("q"), project_id=project_id, title=question))
    provider = get_provider("codex") if llm else None
    sup = DiscoverySupervisor(led, store, project_id, provider=provider)
    cands = sup.generate(question, q.id, context={"variables": ["t", "y"]}, n=n, use_llm=llm)
    typer.echo(f"Generated {len(cands)} candidates (generator={'codex' if llm else 'mock'}):")
    for c in cands:
        typer.echo(f"  {c.id}  [{c.hypothesis_type.value}]  {c.title}")


@hypothesis_app.command("evaluate")
def hypothesis_evaluate(project_id: str = typer.Argument(...)) -> None:
    """Score falsifiability/actionability/specificity for stored candidates."""
    from ..discovery.falsifiability import score_candidate

    _, _, store = _discovery()
    cands = _load_candidates(store, project_id)
    if not cands:
        typer.echo("(no candidates; run 'hypothesis generate' first)")
        return
    for c in cands:
        s = score_candidate(c).as_dict()
        typer.echo(f"  {c.title[:40]:40}  fals={s['falsifiability_score']:.2f} "
                   f"act={s['actionability_score']:.2f} spec={s['specificity_score']:.2f}")


@hypothesis_app.command("tournament")
def hypothesis_tournament(
    project_id: str = typer.Argument(...),
    keep_top: int = typer.Option(4, help="How many to accept"),
) -> None:
    """Run the multiobjective tournament and persist accepted/rejected."""
    from ..discovery.supervisor import DiscoverySupervisor

    _, led, store = _discovery()
    sup = DiscoverySupervisor(led, store, project_id)
    cands = sup.filter_falsifiable(_load_candidates(store, project_id))
    if not cands:
        typer.echo("(no falsifiable candidates)")
        return
    result = sup.tournament(cands, keep_top=keep_top)
    by_id = {c.id: c for c in cands}
    typer.echo(f"Ranking (top {keep_top} accepted, rest rejected & kept):")
    for rank, cid in enumerate(result.ranking):
        mark = "✓" if rank < keep_top else "·"
        typer.echo(f"  {mark} {result.elo[cid]:.0f}  {by_id[cid].title[:44]}")
    typer.echo(f"Diversity: {result.diversity.as_dict()['n_mechanisms']} mechanisms, "
               f"eff_n={result.diversity.effective_num_hypotheses:.2f}")


_FAMILY_BEHAVIOR = {
    "exponential": "monotonic", "damped": "oscillatory", "logistic": "saturating",
    "cubic": "monotonic", "linear": "monotonic", "flexible": "diverging",
    "baseline": "flat", "null": "flat",
}


@experiment_app.command("propose")
def experiment_propose(project_id: str = typer.Argument(...)) -> None:
    """Build a discriminating experiment proposal from accepted hypotheses."""
    from ..discovery.experiment_design import require_discriminating
    from ..discovery.supervisor import DiscoverySupervisor

    _, led, store = _discovery()
    accepted = [c for c in _load_candidates(store, project_id)
                if c.status.value == "ACCEPTED"]
    if len(accepted) < 2:
        typer.echo("Need >=2 accepted candidates; run 'hypothesis tournament' first.")
        raise typer.Exit(1)
    predicted = {}
    for c in accepted:
        text = (c.title + " " + c.mechanism + " " + c.statement).lower()
        fam = next((f for f in _FAMILY_BEHAVIOR if f in text), "linear")
        predicted[c.id] = _FAMILY_BEHAVIOR.get(fam, "monotonic")
    sup = DiscoverySupervisor(led, store, project_id)
    proposal = sup.build_proposal("Discriminate accepted hypotheses", accepted, predicted,
                                  variables=["t", "y"], parameter_space={"seed": [1, 2]})
    try:
        require_discriminating(proposal)
    except ValueError as exc:
        typer.echo(f"Not discriminating: {exc}")
        raise typer.Exit(1) from exc
    sup.critique_proposal(proposal)
    store.put(project_id, "proposal", proposal.id, proposal.model_dump(),
              status="PREREGISTERED", summary="experiment proposed via CLI")
    typer.echo(f"Proposed experiment {proposal.id} testing {len(accepted)} hypotheses.")
    typer.echo(f"  outcomes: {proposal.preregistered_predictions}")


@experiment_app.command("rank")
def experiment_rank(project_id: str = typer.Argument(...)) -> None:
    """Rank stored experiment proposals by research utility."""
    from ..discovery.research_utility import compute_utility

    _, _, store = _discovery()
    proposals = store.list_objects(project_id, kind="proposal")
    if not proposals:
        typer.echo("(no proposals)")
        return
    scored = []
    for p in proposals:
        eig = p.get("expected_information_gain") or 0.5
        comp = {"information_gain": min(1.0, float(eig)), "scientific_value": 0.6,
                "falsification_power": 0.7, "reproducibility": 1.0,
                "human_learning_value": 0.6, "compute_cost": 0.3, "risk": 0.1}
        scored.append((p["id"], compute_utility(comp).utility))
    for pid, u in sorted(scored, key=lambda t: t[1], reverse=True):
        typer.echo(f"  utility={u:.3f}  {pid}")


@experiment_app.command("run")
def experiment_run(
    project_id: str = typer.Argument(..., help="Project id"),
    system: str = typer.Option("exponential_decay", help="Dynamical system to fit"),
    sandbox: str = typer.Option("subprocess", help="subprocess | docker"),
) -> None:
    """Execute the project's discovering experiment via the hidden-dynamics runner."""
    from ..benchmarks.hidden_dynamics import run_hidden_dynamics
    from ..sandbox.runner import get_runner

    _, led, store = _discovery()
    if led.get_project(project_id) is None:
        typer.echo(f"project {project_id} not found")
        raise typer.Exit(1)
    art = repo_root() / "research" / "artifacts" / f"{project_id}_experiment_run"
    rep = run_hidden_dynamics(led, store, project_id, system=system, seeds=[1, 2],
                              artifacts_root=art, runner=get_runner(sandbox))
    typer.echo(f"Ran experiment: winner={rep['winner_family']} reproduced={rep['reproduced']}")


@experiment_app.command("cancel")
def experiment_cancel(node_id: str = typer.Argument(..., help="Research-tree experiment node id"),
                      project_id: str = typer.Option(..., help="Project id")) -> None:
    """Cancel a research-tree experiment node."""
    from ..discovery.tree import NodeStatus, ResearchTree

    _, _, store = _discovery()
    tree = ResearchTree(store, project_id)
    tree.set_status(node_id, NodeStatus.CANCELLED, decision="cancelled via CLI")
    typer.echo(f"Cancelled {node_id}")


@experiment_app.command("resume")
def experiment_resume(project_id: str = typer.Argument(...)) -> None:
    """List runnable (non-completed) experiment nodes for resumption."""
    from ..discovery.tree import ResearchTree

    _, _, store = _discovery()
    tree = ResearchTree(store, project_id)
    frontier = tree.frontier()
    typer.echo(f"Resumable experiment nodes: {len(frontier)}")
    for n in frontier:
        typer.echo(f"  {n.id}  {n.status.value}  {n.title[:50]}")


@discovery_app.command("next")
def discovery_next(project_id: str = typer.Argument(...)) -> None:
    """Recommend the next experiment (with alternatives)."""
    from ..discovery.next_experiment import recommend_next

    _, _, store = _discovery()
    proposals = store.list_objects(project_id, kind="proposal")
    cands = [{"experiment_id": p["id"],
              "eig": p.get("expected_information_gain") or 0.5, "cost": 0.3, "risk": 0.1,
              "hypotheses_discriminated": p.get("hypotheses_tested", []),
              "components": {"information_gain": 0.5, "scientific_value": 0.6,
                             "falsification_power": 0.7, "reproducibility": 1.0,
                             "human_learning_value": 0.6, "compute_cost": 0.3,
                             "time_cost": 0.2, "monetary_cost": 0.0, "risk": 0.1}}
             for p in proposals]
    rec = recommend_next(cands)
    if rec is None:
        typer.echo("(no proposals to recommend from)")
        return
    typer.echo(f"Recommended: {rec.experiment_id}")
    typer.echo(f"  reason: {rec.reason}")
    typer.echo(f"  alternatives: {len(rec.alternatives)} · reason_not_to_run: {rec.reason_not_to_run}")


@discovery_app.command("status")
def discovery_status(project_id: str = typer.Argument(...)) -> None:
    """Summarise the discovery state for a project."""
    _, _, store = _discovery()
    for kind in ("candidate", "proposal", "tree_node", "tool", "negative"):
        items = store.list_objects(project_id, kind=kind)
        typer.echo(f"  {kind}: {len(items)}")
    rejected = store.list_objects(project_id, kind="candidate", status="REJECTED")
    typer.echo(f"  rejected candidates kept: {len(rejected)}")


@discovery_app.command("report")
def discovery_report(project_id: str = typer.Argument(...)) -> None:
    """Print provenance events for the discovery process."""
    _, led, _ = _discovery()
    prov = led.provenance_for_project(project_id)
    disc_actions = {"GENERATE", "RANK", "REJECT", "PRUNE", "CONFIDENCE_UPDATE",
                    "TOOL_APPROVAL", "TOOL_PROPOSAL", "NEXT_EXPERIMENT"}
    events = [p for p in prov if p["action"] in disc_actions]
    typer.echo(f"Discovery provenance events: {len(events)}")
    for ev in events[-20:]:
        typer.echo(f"  {ev['at'][:19]}  {ev['action']:18} {ev['summary'][:60]}")


@benchmark_app.command("hidden-dynamics")
def benchmark_hidden_dynamics(
    system: str = typer.Option("exponential_decay", help="System to discover"),
    seeds: str = typer.Option("1,2", help="Comma-separated seeds"),
    sandbox: str = typer.Option("subprocess", help="subprocess | docker"),
    llm: bool = typer.Option(False, "--llm", help="Use Codex for generation + critique"),
) -> None:
    """Run the Hidden Dynamics Discovery Benchmark (Sprints 5–7 integration)."""
    from ..benchmarks.hidden_dynamics import run_hidden_dynamics
    from ..llm.providers import get_provider
    from ..sandbox.runner import get_runner

    _, led, store = _discovery()
    proj = led.create_project(f"Hidden dynamics: {system}", domain="physics",
                              description="Discovery Engine validation benchmark.")
    seed_list = [int(s) for s in seeds.split(",") if s.strip()]
    art = repo_root() / "research" / "artifacts" / f"{proj.id}_hidden_dynamics"
    provider = get_provider("codex") if llm else None
    rep = run_hidden_dynamics(led, store, proj.id, system=system, seeds=seed_list,
                              artifacts_root=art, use_llm=llm, provider=provider,
                              runner=get_runner(sandbox))
    typer.echo(f"Project {proj.id} · system={system} (hidden family: {rep['hidden_family']})")
    typer.echo(f"Candidates: {rep['n_candidates']} · falsifiable: {rep['n_falsifiable']} · "
               f"rejected kept: {rep['n_rejected_kept']}")
    typer.echo(f"Winner family: {rep['winner_family']} · EIG≈{rep['eig_bits']} bits")
    typer.echo(f"poly9 extrapolation RMSE: {rep['poly9_extrapolation_rmse']:.1f} "
               f"(winner {rep['winner_extrapolation_rmse']:.2f})")
    typer.echo(f"Reproduced: {rep['reproduced']} · negatives: {rep['negative_records']}")
    typer.echo(f"Next experiment: {rep['next_experiment']['experiment_id']} "
               f"(+{len(rep['next_experiment']['alternatives'])} alternatives)")
    typer.echo(f"Artifacts: {art}")
    typer.echo("NOTE: synthetic data; model recovery, NOT scientific discovery.")


def _world(project_id: str):
    from ..world_model.graph import WorldModel

    sf, led, _ = _discovery()
    return led, WorldModel(sf, led, project_id)


@world_app.command("demo")
def world_demo(
    system: str = typer.Option("damped_oscillator", help="System to investigate"),
    exoplanets: bool = typer.Option(False, "--exoplanets",
                                    help="Also download+ingest REAL NASA exoplanet data (authorized)"),
) -> None:
    """Run an investigation, fold it into the World Model, and narrate what changed."""

    from ..benchmarks.hidden_dynamics import run_hidden_dynamics
    from ..discovery.store import DiscoveryStore
    from ..world_model.evolution import evolution_report, snapshot
    from ..world_model.graph import WorldModel
    from ..world_model.narrate import narrate
    from ..world_model.programs import create_program
    from ..world_model.update import integrate_hidden_dynamics
    from ..world_model.viz import write_html

    sf, led, store = _discovery()
    store = DiscoveryStore(sf, led)
    proj = led.create_project(f"World Model: {system}", domain="astronomy")
    wm = WorldModel(sf, led, proj.id)
    prog = create_program(wm, "Dynamics research program", domain="astronomy")

    art = repo_root() / "research" / "artifacts" / f"{proj.id}_world"
    # First investigation creates the belief nodes; snapshot AFTER so the second
    # investigation's updates show up as 'believe_more' (accumulating replication).
    rep1 = run_hidden_dynamics(led, store, proj.id, system=system, seeds=[1, 2],
                               artifacts_root=str(art))
    integrate_hidden_dynamics(wm, rep1, program_id=prog.id)
    before = snapshot(wm)
    rep2 = run_hidden_dynamics(led, store, proj.id, system=system, seeds=[3, 4],
                               artifacts_root=str(art))
    integrate_hidden_dynamics(wm, rep2, program_id=prog.id)
    after = snapshot(wm)

    if exoplanets:
        from ..world_model.ingest import download_exoplanets, ingest_exoplanets
        csv_path = repo_root() / "research" / "datasets" / "exoplanets.csv"
        meta = download_exoplanets(csv_path, authorized=True)
        king = ingest_exoplanets(wm, csv_path, program_id=prog.id, manifest=meta)
        law_node = wm.get_node(king["law_id"])
        conf = law_node.confidence if law_node else 0.0
        typer.echo(f"Kepler on REAL data: n={king['n_rows']} R²={king['fit']['r2']} "
                   f"→ belief {conf:.2f}")

    evo = evolution_report(wm, before, after)
    typer.echo(f"Project {proj.id} · nodes {wm.stats()['n_nodes']} edges {wm.stats()['n_edges']}")
    typer.echo(f"believe_more: {len(evo['believe_more'])} · new contradictions: "
               f"{len(evo['new_contradictions'])} · new anomalies: {len(evo['new_anomalies'])}")
    typer.echo("--- ACERO says ---")
    for s in narrate(wm):
        typer.echo(f"  • {s['text']}")
    html_path = write_html(wm, str(art / "world.html"))
    typer.echo(f"Visualization: {html_path}")


@world_app.command("stats")
def world_stats(project_id: str = typer.Argument(...)) -> None:
    """Node/edge counts for a project's World Model."""
    _, wm = _world(project_id)
    import json as _json
    typer.echo(_json.dumps(wm.stats(), indent=2))


@world_app.command("narrate")
def world_narrate(project_id: str = typer.Argument(...)) -> None:
    """What ACERO can now say about the accumulated knowledge."""
    from ..world_model.narrate import narrate

    _, wm = _world(project_id)
    statements = narrate(wm)
    if not statements:
        typer.echo("(no statements yet)")
        return
    for s in statements:
        typer.echo(f"• [{s['kind']}] {s['text']}")


@world_app.command("viz")
def world_viz(project_id: str = typer.Argument(...),
              out: str = typer.Option("", help="Output HTML path")) -> None:
    """Write an HTML visualization of the World Model."""
    from ..world_model.viz import write_html

    _, wm = _world(project_id)
    path = out or str(repo_root() / "research" / "artifacts" / f"{project_id}_world.html")
    typer.echo(f"Wrote {write_html(wm, path)}")


@world_app.command("query")
def world_query(project_id: str = typer.Argument(...),
                what: str = typer.Argument(..., help="anomalies|untested|weak|single|contradictions")) -> None:
    """Query the scientific memory."""
    import json as _json
    from collections.abc import Callable

    from ..world_model.queries import ScientificMemory

    _, wm = _world(project_id)
    mem = ScientificMemory(wm)
    table: dict[str, Callable[[], object]] = {
        "anomalies": lambda: [a.label for a in mem.open_anomalies()],
        "contradictions": lambda: [c.label for c in mem.open_contradictions()],
        "untested": lambda: [n.label for n in mem.untested_beliefs()],
        "weak": mem.weak_relations,
        "single": lambda: [n.label for n in mem.single_source_claims()],
        "critical": mem.critical_assumptions,
    }
    fn = table.get(what)
    if fn is None:
        typer.echo(f"unknown query '{what}'; choose from {sorted(table)}")
        raise typer.Exit(1)
    typer.echo(_json.dumps(fn(), indent=2, ensure_ascii=False))


@app.command("pilot")
def pilot_run(
    title: str = typer.Option("ACERO cooling-law pilot", help="Project title"),
    seeds: str = typer.Option("1,2,3", help="Comma-separated seeds"),
    sandbox: str = typer.Option("subprocess", help="Sandbox backend: subprocess | docker"),
    llm: str = typer.Option("", help="Enable LLM-assisted skeptic: '' | codex | mock"),
) -> None:
    """Run the Sprint-4 computational research pilot end to end."""
    from ..experiment.orchestrator import run_pilot
    from ..sandbox.runner import get_runner

    led = _ledger()
    proj = led.create_project(title, domain="physics",
                              description="Symbolic-discovery pilot on synthetic cooling data.")
    seed_list = [int(s) for s in seeds.split(",") if s.strip()]
    art = repo_root() / "research" / "artifacts" / f"{proj.id}_pilot"

    runner = get_runner(sandbox)
    provider = None
    if llm:
        from ..llm.providers import get_provider
        provider = get_provider(llm)

    rep = run_pilot(led, proj.id, artifacts_root=art, seeds=seed_list,
                    runner=runner, llm_provider=provider)
    typer.echo(f"Project {proj.id}")
    typer.echo(f"Best model: {rep['overall_best_model']} {rep['best_counts']}")
    typer.echo(f"Recovered k={rep['mean_recovered_k']:.4f} (true {rep['true_k']})")
    typer.echo(f"Reproduced: {rep['reproduced']}")
    typer.echo(f"Skeptic (rule-based): {rep['skeptic']['n_objections']} objections, "
               f"{rep['skeptic']['n_failed_checks']} failed checks")
    if rep.get("llm_skeptic"):
        ls = rep["llm_skeptic"]
        typer.echo(f"Skeptic (LLM, advisory): provider={ls.get('provider')} "
                   f"available={ls.get('available')} objections={len(ls.get('objections', []))}")
    typer.echo(f"Artifacts: {art}")
    typer.echo("NOTE: recovering a known law is NOT a discovery. LLM notes are advisory, not evidence.")


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
