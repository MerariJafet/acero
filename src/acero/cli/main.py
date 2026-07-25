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
cognitive_app = typer.Typer(help="Cognitive Discovery Engine: concepts, analogies, first principles")
inference_app = typer.Typer(help="Governing Structure Inference Engine")
learner_app = typer.Typer(help="Human Understanding Engine: learner profile")
learn_app = typer.Typer(help="Human Understanding Engine: explain / predict / assess / gate")
gate_app = typer.Typer(help="Global Epistemic Gate")
app.add_typer(project_app, name="project")
app.add_typer(domain_app, name="domain")
app.add_typer(hypothesis_app, name="hypothesis")
app.add_typer(experiment_app, name="experiment")
app.add_typer(discovery_app, name="discovery")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(world_app, name="world")
app.add_typer(cognitive_app, name="cognitive")
app.add_typer(inference_app, name="inference")
domains_app = typer.Typer(help="Scientific Domain Labs (Sprint 10)")
reliability_app = typer.Typer(help="Scientific Reliability & Adversarial Assurance (Sprint 11)")
publication_app = typer.Typer(help="Publication candidates (never auto-publishes)")
secrets_app = typer.Typer(help="Local HMAC secret management (Sprint 14)")
worker_app = typer.Typer(help="Persistent research worker runtime (Sprint 14)")
program_app = typer.Typer(help="Research Program Operating System (Sprint 16)")
studies_app = typer.Typer(help="Executed research studies on real data (Sprint 17)")
db_app = typer.Typer(help="Database migrations (Alembic, Sprint 22)")
evaluation_app = typer.Typer(help="Scientific Capability Evaluation Engine (Sprint 18)")
collab_app = typer.Typer(help="Collaboration & External Review Preparation (Sprint 19)")
backup_app = typer.Typer(help="Local backup / verify / restore (Sprint 20)")
release_app = typer.Typer(help="Release candidate manifest + acceptance (Sprint 20)")
science_app = typer.Typer(help="Scientific Constitution (CCC): discovery/confirmation, causality, independence")
app.add_typer(learner_app, name="learner")
app.add_typer(learn_app, name="learn")
app.add_typer(gate_app, name="gate")
app.add_typer(domains_app, name="domains")
app.add_typer(reliability_app, name="reliability")
app.add_typer(publication_app, name="publication")
app.add_typer(secrets_app, name="secrets")
app.add_typer(worker_app, name="worker")
app.add_typer(program_app, name="program")
app.add_typer(studies_app, name="studies")
app.add_typer(db_app, name="db")
app.add_typer(evaluation_app, name="evaluation")
app.add_typer(collab_app, name="collab")
app.add_typer(backup_app, name="backup")
app.add_typer(release_app, name="release")
app.add_typer(science_app, name="science")


def _understanding():
    """Return a HumanUnderstandingEngine bound to the persistent store."""
    from ..understanding.engine import HumanUnderstandingEngine
    from ..understanding.store import UnderstandingStore

    _, _, store = _discovery()
    return HumanUnderstandingEngine(UnderstandingStore(store))


def _ledger() -> ResearchLedger:
    return ResearchLedger(default_session_factory())


def _discovery():
    """Return (session_factory, ledger, store) bound to the same DB."""
    from ..discovery.store import DiscoveryStore

    sf = default_session_factory()
    led = ResearchLedger(sf)
    return sf, led, DiscoveryStore(sf, led)


@app.command()
def doctor(deep: bool = typer.Option(False, "--deep", help="run the v2 deep diagnostic")) -> None:
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

    if deep:
        ok = _doctor_deep() and ok

    typer.echo("OK ✓" if ok else "PROBLEMS FOUND ✗")
    raise typer.Exit(code=0 if ok else 1)


def _doctor_deep() -> bool:
    """v2 deep diagnostic: DB/migrations, schemas, write surface, tokens, gates, runtime,
    disk, secrets, git. Returns True if all critical checks pass."""
    ok = True
    typer.echo("\n--- deep diagnostic (v2) ---")

    def check(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        mark = "✓" if passed else "✗"
        typer.echo(f"  [{mark}] {name}{': ' + detail if detail else ''}")
        if not passed:
            ok = False

    # DB + schema version
    try:
        from ..core.schema_version import check as schema_check
        from ..core.schema_version import ensure_stamped
        sf = default_session_factory()
        ensure_stamped(sf)
        st = schema_check(sf)
        check("schema version", st.compatible, f"db={st.db_version} code={st.code_version} · {st.detail}")
    except Exception as exc:  # noqa: BLE001
        check("schema version", False, str(exc))

    # policies
    try:
        load_policies()
        guard = PolicyGuard()
        check("policies + no paid services", not guard.paid_llm_allowed())
    except Exception as exc:  # noqa: BLE001
        check("policies", False, str(exc))

    # global gate rules present (write surface protected)
    try:
        from ..epistemic_gate.registry import GateRegistry
        n_rules = len(GateRegistry().all_rules())
        check("epistemic gate rules loaded", n_rules >= 80, f"{n_rules} rules")
    except Exception as exc:  # noqa: BLE001
        check("epistemic gate", False, str(exc))

    # mutation tokens
    try:
        from ..epistemic_gate.tokens import TokenError, TokenRegistry
        reg = TokenRegistry(ttl_seconds=30)
        tok = reg.issue(action="doctor", project_id="_")
        reg.validate(tok, action="doctor", project_id="_")
        reg.spend(tok)
        replay_blocked = False
        try:
            reg.validate(tok, action="doctor", project_id="_")
        except TokenError:
            replay_blocked = True
        check("mutation tokens (issue/validate/replay-block)", replay_blocked)
    except Exception as exc:  # noqa: BLE001
        check("mutation tokens", False, str(exc))

    # runtime backend (Sprint 14) — informational until installed, then a real check
    try:
        from ..runtime.store import RuntimeStore
        RuntimeStore(default_session_factory())
        check("persistent runtime backend", True)
    except ImportError:
        typer.echo("  [i] persistent runtime backend not installed (Sprint 14)")
    except Exception as exc:  # noqa: BLE001
        check("persistent runtime backend", False, str(exc))

    # secrets (Sprint 14) — env-provided HMAC secret status (never shows the secret)
    try:
        from ..runtime.secrets import secret_status
        s = secret_status()
        check("secret management", True, f"mode={s['mode']} key_id={s['key_id']}")
    except ImportError:
        typer.echo("  [i] secret management not installed (Sprint 14)")
    except Exception as exc:  # noqa: BLE001
        check("secret management", False, str(exc))

    # schemas exported + up to date
    try:
        import subprocess as _sp
        r = _sp.run([sys.executable, "scripts/export_schemas.py", "--check"],
                    cwd=str(repo_root()), capture_output=True, text=True)
        check("exported JSON schemas up to date", r.returncode == 0)
    except Exception as exc:  # noqa: BLE001
        check("schemas", False, str(exc))

    # disk headroom
    try:
        import shutil as _sh
        free_gb = _sh.disk_usage(str(repo_root())).free / 1e9
        check("disk headroom", free_gb > 0.5, f"{free_gb:.1f} GB free")
    except Exception as exc:  # noqa: BLE001
        check("disk", False, str(exc))

    # vestigial packages (informational, never fails)
    for pkg in ("hypothesis", "integrations", "knowledge"):
        p = repo_root() / "src" / "acero" / pkg
        if p.exists():
            typer.echo(f"  [i] vestigial package '{pkg}' retained (see architecture audit)")

    # git
    try:
        import subprocess as _sp
        branch = _sp.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                         cwd=str(repo_root()), capture_output=True, text=True).stdout.strip()
        typer.echo(f"  [i] git branch: {branch}")
    except Exception:  # noqa: BLE001
        pass

    return ok


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


@cognitive_app.command("benchmark")
def cognitive_benchmark(
    sandbox: str = typer.Option("subprocess", help="subprocess | docker"),
    no_transfer: bool = typer.Option(False, "--no-transfer", help="Skip sandbox transfer test"),
) -> None:
    """Run the Cross-Domain Structural Discovery Benchmark (Sprints 8.5–8.7)."""
    from ..benchmarks.cross_domain import run_cross_domain
    from ..sandbox.runner import get_runner
    from ..world_model.graph import WorldModel

    sf, led, _ = _discovery()
    proj = led.create_project("Cross-domain structural discovery", domain="physics")
    wm = WorldModel(sf, led, proj.id)
    rep = run_cross_domain(wm, runner=get_runner(sandbox), run_transfer=not no_transfer)
    typer.echo(f"Project {proj.id}")
    for name, a in rep["analogies"].items():
        integ = rep["integrations"][name]
        typer.echo(f"  {name}: {a['status']} (deep={a['deep_score']}) → "
                   f"{integ['outcome']} conf={integ['confidence']:.2f}")
    pg = rep["first_principles"]["oscillator_dimensional_analysis"]["pi_groups"]
    typer.echo(f"  oscillator Pi groups: {pg}")
    typer.echo("NOTE: known correspondences — validates the METHOD, not a discovery.")


@cognitive_app.command("analogy")
def cognitive_analogy(
    pair: str = typer.Argument("oscillator_rlc",
                               help="oscillator_rlc | thermal_particle_diffusion | atom_solar_system"),
) -> None:
    """Build and validate one benchmark analogy (persisted to a fresh World Model)."""
    from ..cognitive.analogies.engine import AnalogyEngine
    from ..cognitive.analogies.systems import BENCHMARK_PAIRS
    from ..world_model.graph import WorldModel

    if pair not in BENCHMARK_PAIRS:
        typer.echo(f"unknown pair; choose from {sorted(BENCHMARK_PAIRS)}")
        raise typer.Exit(1)
    sf, led, _ = _discovery()
    proj = led.create_project(f"Analogy: {pair}", domain="physics")
    wm = WorldModel(sf, led, proj.id)
    a = AnalogyEngine(wm).build(*BENCHMARK_PAIRS[pair])
    typer.echo(f"{a.source_system} ~ {a.target_system}")
    typer.echo(f"  status: {a.status.value} · deep_score: {a.scores.deep_score()} · "
               f"surface: {a.scores.surface_similarity}")
    typer.echo(f"  mapping: {a.entity_mapping}")
    for v in a.validations:
        typer.echo(f"  [{'✓' if v.passed else '✗'}] {v.test}: {v.detail}")


@cognitive_app.command("dimensions")
def cognitive_dimensions(
    variables: str = typer.Argument(
        "period=time,length=length,gravity=acceleration,mass=mass",
        help="comma-separated var=dimension pairs"),
) -> None:
    """Dimensional analysis: Buckingham-Pi groups of the given variables."""
    from ..cognitive.first_principles.engine import FirstPrinciplesEngine
    from ..cognitive.first_principles.models import FirstPrinciplesProblem

    var_map = dict(p.split("=", 1) for p in variables.split(",") if "=" in p)
    prob = FirstPrinciplesProblem(project_id="cli", phenomenon="cli", variables=var_map)
    res = FirstPrinciplesEngine().dimensional_analysis(prob)
    import json as _json
    typer.echo(_json.dumps(res, indent=2))


@cognitive_app.command("validate-equation")
def cognitive_validate_equation(
    lhs: str = typer.Argument(..., help="lhs dimension name"),
    rhs: str = typer.Argument(..., help="rhs dimension name"),
) -> None:
    """Check whether an equation lhs = rhs is dimensionally consistent."""
    from ..cognitive.first_principles.engine import FirstPrinciplesEngine

    res = FirstPrinciplesEngine().validate_equation(lhs, rhs)
    mark = "✓ consistent" if res["consistent"] else "✗ INCONSISTENT"
    typer.echo(f"{lhs} = {rhs}: {mark}  ({res['lhs']} vs {res['rhs']})")


_SYSTEMS = ["exponential_decay", "logistic", "harmonic", "damped", "predator_prey"]


@inference_app.command("discover")
def inference_discover(
    system: str = typer.Argument("damped", help=f"one of {_SYSTEMS}"),
    noise: float = typer.Option(0.0, help="observation noise"),
    threshold: float = typer.Option(0.2, help="sparsity threshold"),
) -> None:
    """Infer governing structure of a synthetic (hidden-equation) system."""
    from ..inference.data.observations import generate
    from ..inference.engine import StructureInferenceEngine
    from ..inference.models import StructureInferenceProblem

    if system not in _SYSTEMS:
        typer.echo(f"unknown system; choose from {_SYSTEMS}")
        raise typer.Exit(1)
    obs = generate(system, seed=1, n=500, t_max=8.0, noise=noise)
    prob = StructureInferenceProblem(project_id="cli", phenomenon=system,
                                     variables_observed=obs.variables)
    rep = StructureInferenceEngine().infer(prob, obs, threshold=threshold,
                                           derivative_method="savgol" if noise > 0 else "auto")
    typer.echo(f"System: {system} · level: {rep['inference_level']} · "
               f"abstains: {rep['abstention']['abstains']}")
    for tgt, e in rep["equations"].items():
        typer.echo(f"  {tgt} = {e['expression']}   (R²={e['r2']}, ident={e['identifiability']})")
    if rep["invariants"]:
        i = rep["invariants"][0]
        typer.echo(f"  invariant: {i['expression']} [{i['classification']}]")
    typer.echo("NOTE: identified from an IMPOSED library — a fitted equation is NOT a law.")


@inference_app.command("benchmark")
def inference_benchmark() -> None:
    """Run the Governing Dynamics Inference Benchmark (7 levels)."""
    from ..benchmarks.governing_dynamics import run_governing_dynamics

    r = run_governing_dynamics()
    typer.echo("L1 recovery: " + ", ".join(
        f"{k}={'✓' if v['recovered'] else '✗'}" for k, v in r["level1_recovery"].items()))
    typer.echo("L2 noise (R² dv/dt): " + ", ".join(
        f"{k}={v['r2_dv']:.2f}" for k, v in r["level2_noise"].items()))
    typer.echo(f"L3 omitted variable flagged: {r['level3_omitted_variable']['missing_variable_flagged']}")
    typer.echo(f"L4 discriminating experiment: divergence="
               f"{r['level4_equivalence']['discriminating_experiment']['predicted_divergence']}")
    typer.echo(f"L5 regime change detected: {r['level5_regime']['regime_change_detected']}")
    typer.echo(f"L6 invariant: {r['level6_conservation']['invariant']} "
               f"[{r['level6_conservation']['classification']}]")
    typer.echo(f"L7 adversarial gate: {r['level7_adversarial_gate']['status']} "
               f"({r['level7_adversarial_gate']['n_blockers']} blockers)")
    typer.echo("NOTE: synthetic data, hidden equations — validates the METHOD, not a discovery.")


@inference_app.command("sunspots")
def inference_sunspots() -> None:
    """Download and analyse the real SILSO sunspot series (authorized public dataset)."""
    from ..benchmarks.real_astronomy_inference import analyze_sunspots, download_sunspots

    path = repo_root() / "research" / "datasets" / "sunspots.csv"
    meta = download_sunspots(path, authorized=True)
    r = analyze_sunspots(path, manifest=meta)
    typer.echo(f"SILSO sunspots: n={r['n']} span={r['time_span_years']} "
               f"(sha {meta['sha256'][:16]})")
    typer.echo(f"  dominant period: {r['dominant_period_years']} yr → {r['classification']}")
    typer.echo(f"  low-activity decades: {r['low_activity_decades'][:6]}")
    typer.echo(f"  {r['cannot_conclude'][0]}")


@inference_app.command("gate")
def inference_gate(bad: bool = typer.Option(False, "--bad", help="submit a flawed candidate")) -> None:
    """Run the mandatory epistemic gate on a demo candidate."""
    from ..inference.audit.gate import GateInput, evaluate
    from ..inference.models import IdentifiabilityStatus

    gi = GateInput() if not bad else GateInput(
        dimensions_valid=False, reproduced=False, makes_causal_claim=True,
        n_equivalent_models=3, counts_equivalent_as_new=True, codex_treated_as_evidence=True,
        identifiability=IdentifiabilityStatus.NON_IDENTIFIABLE, presented_as_unique=True)
    rep = evaluate(gi)
    typer.echo(f"Gate status: {rep.status.value}")
    for f in rep.findings:
        typer.echo(f"  [{f.severity}] {f.rule}: {f.detail}")


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


# --- Human Understanding Engine (Sprint 9) --------------------------------

@learner_app.command("init")
def learner_init(
    name: str = typer.Option("researcher", help="preferred name"),
    domains: str = typer.Option("", help="comma-separated research domains"),
) -> None:
    """Create the local learner profile."""
    eng = _understanding()
    profile = eng.init_learner(
        preferred_name=name,
        research_domains=[d.strip() for d in domains.split(",") if d.strip()])
    typer.echo(f"learner: {profile.learner_id} ({profile.preferred_name})")


@learner_app.command("profile")
def learner_profile() -> None:
    """Show the local learner profile(s)."""
    eng = _understanding()
    assert eng.store is not None
    profiles = eng.store.profiles()
    if not profiles:
        typer.echo("no learner profile yet — run 'acero learner init'")
        return
    for p in profiles:
        typer.echo(f"{p.learner_id}: {p.preferred_name} domains={p.research_domains}")


@learner_app.command("status")
def learner_status(learner_id: str = typer.Argument(...)) -> None:
    """Show knowledge status: mastered / partial / misconceived."""
    eng = _understanding()
    s = eng.status(learner_id)
    typer.echo(f"learner {learner_id}: {s['n_states']} concept states")
    typer.echo(f"  mastered: {s['mastered']}")
    typer.echo(f"  partial: {s['partial']}")
    typer.echo(f"  misconceived: {s['misconceived']}")
    typer.echo(f"  open misconceptions: {s['open_misconceptions']}")


@learner_app.command("history")
def learner_history(learner_id: str = typer.Argument(...)) -> None:
    """Show the learning history."""
    eng = _understanding()
    assert eng.store is not None
    events = eng.store.history(learner_id)
    typer.echo(f"{len(events)} learning events")
    for e in events[-20:]:
        typer.echo(f"  [{e.get('kind')}] {e.get('concept')}: {e.get('detail')}")


@learn_app.command("requirements")
def learn_requirements(
    kind: str = typer.Argument("sindy", help="sindy | analogy | sunspots"),
    project_id: str = typer.Option("proj", help="research project id"),
) -> None:
    """Show research-derived learning requirements."""
    from ..understanding.curriculum.research_curriculum import requirements_for

    for r in requirements_for(kind, project_id):
        flag = "BLOCKING" if r.blocking else r.criticality.value
        typer.echo(f"  [{flag}] {r.concept}: {r.reason_required}")
        if r.prerequisite_concepts:
            typer.echo(f"        prereqs: {r.prerequisite_concepts}")


@learn_app.command("explain")
def learn_explain(
    subject: str = typer.Argument("sindy_damped"),
    level: str = typer.Option("intuition", help="intuition|conceptual|mathematical|computational|frontier"),
) -> None:
    """Show a layered explanation of a real result."""
    from ..understanding.explanation.levels import build_levels
    from ..understanding.models import ExplanationLevel

    arts = build_levels(
        subject, phenomenon="damped oscillation", variables=["x", "v"],
        mechanism="restoring force minus friction", assumptions=["linear damping"],
        equations=["dx/dt = v", "dv/dt = -4x - 0.5v"],
        code_references=["inference/engine.py"],
        evidence_references=["benchmarks/governing_dynamics.py"],
        limitations=["polynomial library imposed", "derivatives from same data"])
    want = ExplanationLevel(level)
    art = next(a for a in arts if a.level == want)
    typer.echo(f"[{art.level.value}] {art.subject}\n{art.content}")
    if art.equations:
        typer.echo(f"  equations: {art.equations}")
    typer.echo(f"  limitations: {art.limitations}")
    typer.echo(f"  question: {art.questions[0] if art.questions else '—'}")


@learn_app.command("assess")
def learn_assess(
    learner_id: str = typer.Argument(...),
    concept: str = typer.Option("imposed_library"),
    response: str = typer.Option(..., help="your explanation"),
    expect: str = typer.Option("imposed library,fit not law", help="comma-separated expected elements"),
) -> None:
    """Grade an open-ended response and update knowledge state."""
    from ..understanding.models import EvidenceType

    eng = _understanding()
    ev, update = eng.record_assessment(
        learner_id, concept, EvidenceType.EXPLAIN_OWN_WORDS,
        "explain in your own words", response,
        [e.strip() for e in expect.split(",") if e.strip()])
    typer.echo(f"score={ev.score} status: {update.from_status} -> {update.to_status}")
    if update.misconceptions_detected:
        typer.echo(f"  misconceptions detected: {update.misconceptions_detected}")


@learn_app.command("transfer")
def learn_transfer(
    learner_id: str = typer.Argument(...),
    concept: str = typer.Option("identifiability"),
    response: str = typer.Option(..., help="your transfer answer"),
) -> None:
    """Assess cross-domain transfer of a concept."""
    from ..understanding.assessment.transfer import assess_transfer

    ev, grade = assess_transfer(learner_id, concept, response)
    typer.echo(f"transfer score={ev.score} (pass={ev.score >= 0.7})")
    if grade.red_flags:
        typer.echo(f"  red flags: {grade.red_flags}")


@learn_app.command("gate")
def learn_gate(
    learner_id: str = typer.Argument(...),
    decision: str = typer.Option("claim_novelty"),
    concepts: str = typer.Option("imposed_library,governing_structure"),
) -> None:
    """Run the human comprehension gate for a critical decision."""
    eng = _understanding()
    res = eng.comprehension_gate(
        learner_id, decision,
        [c.strip() for c in concepts.split(",") if c.strip()])
    typer.echo(f"comprehension gate [{decision}]: {res.status.value}")
    for b in res.blockers:
        typer.echo(f"  ⛔ {b}")


@learn_app.command("dashboard")
def learn_dashboard(
    learner_id: str = typer.Argument(...),
    kind: str = typer.Option("sindy", help="research curriculum to show"),
    out: str = typer.Option("", help="output HTML path"),
) -> None:
    """Render the Human Understanding dashboard to an HTML file."""
    from ..understanding.curriculum.research_curriculum import requirements_for
    from ..understanding.dashboard import write_html

    eng = _understanding()
    assert eng.store is not None
    profile = eng.store.load_profile(learner_id)
    path = out or str(repo_root() / "research" / "artifacts" / f"understanding_{learner_id}.html")
    write_html(
        path,
        learner_name=profile.preferred_name if profile else learner_id,
        status=eng.status(learner_id),
        knowledge=[s.model_dump() for s in eng.store.states(learner_id)],
        requirements=[r.model_dump() for r in requirements_for(kind, "proj")],
        misconceptions=[m.model_dump() for m in eng.store.misconceptions(learner_id)],
        predictions=[p.model_dump() for p in eng.store.predictions(learner_id)])
    typer.echo(f"dashboard written: {path}")


@learn_app.command("benchmark")
def learn_benchmark() -> None:
    """Run the Human-in-the-Loop Scientific Understanding Benchmark."""
    from ..benchmarks.human_understanding import run_human_understanding

    r = run_human_understanding()
    c1, c4 = r["case_1_sindy"], r["case_4_adversarial_gate"]
    typer.echo(f"C1 SINDy: status={c1['concept_status']} "
               f"misconception={bool(c1['misconception_detected'])} "
               f"novelty_blocked={c1['novelty_blocked']}")
    typer.echo(f"C2 analogy: status={r['case_2_analogy']['concept_status']} "
               f"rejects_equivalence={r['case_2_analogy']['rejects_equivalence']}")
    typer.echo(f"C3 sunspots: distinguishes_pattern_mechanism="
               f"{r['case_3_sunspots']['distinguishes_pattern_mechanism']}")
    typer.echo(f"C4 adversarial gate: {c4['gate_outcome']} "
               f"({c4['n_blockers']} blockers), human_detected={c4['human_detected_score']}")
    typer.echo(f"transfer: pass={r['transfer']['transfer_pass']} "
               f"wrong_flagged={bool(r['transfer']['wrong_answer_flagged'])}")
    typer.echo(f"prediction: {r['prediction']['comparison']} "
               f"overconfident={r['prediction']['overconfident']}")
    typer.echo("NOTE: validates the METHOD (measuring understanding), not any human.")


# --- Global Epistemic Gate (Sprint 9) -------------------------------------

@gate_app.command("rules")
def gate_rules(stage: str = typer.Option("", help="restrict to one stage")) -> None:
    """List the gate rules (optionally for one stage)."""
    from ..epistemic_gate.models import Stage
    from ..epistemic_gate.registry import GateRegistry

    reg = GateRegistry()
    if stage:
        ids = reg.rule_ids(Stage(stage.upper()))
        typer.echo(f"{stage.upper()}: {len(ids)} rules")
        for i in ids:
            typer.echo(f"  - {i}")
    else:
        for s in Stage:
            typer.echo(f"{s.value}: {len(reg.rule_ids(s))} rules")
        typer.echo(f"total: {len(reg.all_rules())} rules")


@gate_app.command("check")
def gate_check(
    stage: str = typer.Argument(..., help="pipeline stage, e.g. INFERENCE"),
    bad: bool = typer.Option(False, "--bad", help="use a flawed inference artifact"),
) -> None:
    """Run the global epistemic gate for a stage on a demo artifact."""
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import Stage
    from ..epistemic_gate.reports import render
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput

    st = Stage(stage.upper())
    if st == Stage.INFERENCE:
        gi = GateInput() if not bad else GateInput(
            dimensions_valid=False, train_test_disjoint=False, reproduced=False,
            makes_causal_claim=True, codex_treated_as_evidence=True)
        artifact = artifact_from_gate_input(gi)
    else:
        artifact = {}      # empty → rules report as 'cannot evaluate' warnings
    res = GlobalGate().check(st, artifact)
    typer.echo(render(res))


@gate_app.command("report")
def gate_report() -> None:
    """Run the full pipeline gate on a demo set of artifacts."""
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import Stage
    from ..epistemic_gate.reports import render_pipeline
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput

    artifacts = {
        Stage.EXECUTION: {"ran_in_sandbox": True, "secrets_exposed": False,
                          "unauthorized_network": False, "environment_recorded": True,
                          "seeds_recorded": True, "hashes_recorded": True,
                          "timeout_configured": True, "code_modified_unversioned": False,
                          "reproduced": True},
        Stage.INFERENCE: artifact_from_gate_input(GateInput()),
    }
    typer.echo(render_pipeline(GlobalGate().run_pipeline(artifacts)))


@gate_app.command("audit")
def gate_audit() -> None:
    """Adversarial audit of the gate's own coverage."""
    from ..epistemic_gate.audit import rules_audit

    rep = rules_audit()
    typer.echo(f"gate self-audit: {rep.as_dict()['n_findings']} findings")
    for f in rep.findings:
        typer.echo(f"  [{f.severity}] {f.concern}: {f.detail}")


# --- Scientific Domain Labs (Sprint 10) -----------------------------------

@domains_app.command("list")
def domains_list() -> None:
    """List the scientific domain labs."""
    from ..domains.core.registry import all_labs

    for lab in all_labs():
        d = lab.domain()
        typer.echo(f"  {d.id:10s} {d.name}  [safety={d.safety_class.value}]")


@domains_app.command("inspect")
def domains_inspect(domain: str = typer.Argument(...)) -> None:
    """Inspect a domain lab (ontology, concepts, models, gate rules)."""
    from ..domains.core.registry import get_lab

    d = get_lab(domain).domain()
    typer.echo(f"{d.name}\n  ontology: {d.ontology}")
    typer.echo(f"  concepts: {[c.name for c in d.concepts]}")
    typer.echo(f"  models: {[m.name for m in d.models]}")
    typer.echo(f"  solvers: {d.solvers}")
    typer.echo(f"  gate rules: {d.gate_rule_ids}")


@domains_app.command("capabilities")
def domains_capabilities(domain: str = typer.Argument(...)) -> None:
    """Show what a domain lab can and cannot do."""
    from ..domains.core.registry import get_lab

    c = get_lab(domain).domain().capabilities
    typer.echo(f"CAN: {c.can_do}")
    typer.echo(f"CANNOT: {c.cannot_do}")
    typer.echo(f"approximations: {c.approximations}")
    typer.echo(f"needs collaboration: {c.needs_collaboration}")


@domains_app.command("gate-rules")
def domains_gate_rules(domain: str = typer.Argument(...)) -> None:
    """Show the domain-specific gate rules."""
    from ..domains.core.registry import get_lab

    typer.echo("\n".join(f"  - {r}" for r in get_lab(domain).domain().gate_rule_ids))


@domains_app.command("benchmark")
def domains_benchmark(domain: str = typer.Argument(...)) -> None:
    """Run a domain lab's benchmark suite."""
    from ..domains.core.registry import get_lab

    b = get_lab(domain).benchmark()
    for name, case in b.items():
        typer.echo(f"  {'✓' if case.get('passed') else '✗'} {name}")
    typer.echo(f"{sum(bool(c['passed']) for c in b.values())}/{len(b)} cases pass")


def _domain_bench_cmd(domain: str):
    def _cmd() -> None:
        from ..domains.core.registry import get_lab
        b = get_lab(domain).benchmark()
        for name, case in b.items():
            typer.echo(f"  {'✓' if case.get('passed') else '✗'} {name}")
        typer.echo(f"{sum(bool(c['passed']) for c in b.values())}/{len(b)} cases pass")
    return _cmd


for _d in ("physics", "astronomy", "genetics", "chemistry"):
    _sub = typer.Typer(help=f"{_d.title()} Lab")
    _sub.command("benchmark")(_domain_bench_cmd(_d))
    app.add_typer(_sub, name=_d)


@benchmark_app.command("multi-domain")
def benchmark_multi_domain() -> None:
    """Run the Multi-Domain Scientific Reasoning Benchmark."""
    from ..benchmarks.multi_domain import run_multi_domain

    r = run_multi_domain()
    for track, data in r.items():
        typer.echo(f"{track}: {data}")
    typer.echo("NOTE: computational labs — a simulation is NOT experimental validation.")


# --- Inline gate observability + bypass (Sprint 10) -----------------------

@gate_app.command("bypass-test")
def gate_bypass_test() -> None:
    """Attempt seven gate bypasses; all must be blocked."""
    from ..benchmarks.gate_bypass import run_gate_bypass

    r = run_gate_bypass()
    for name, blocked in r["checks"].items():
        typer.echo(f"  {'BLOCKED' if blocked else 'LEAKED!'}  {name}")
    typer.echo(f"all blocked: {r['all_blocked']} ({r['n_blocked']}/{r['n']})")


@gate_app.command("metrics")
def gate_metrics() -> None:
    """Show a demo run's inline-gate metrics."""
    from ..benchmarks.gate_bypass import run_gate_bypass

    run_gate_bypass()
    typer.echo("inline gate metrics are per-enforcer; see 'gate bypass-test' for a live run")


# --- Hybrid grader (Sprint 10) --------------------------------------------

@learner_app.command("grade-hybrid")
def learner_grade_hybrid(
    response: str = typer.Option(..., help="the learner response"),
    concept: str = typer.Option("governing_structure"),
) -> None:
    """Grade a response with the hybrid grader (deterministic authority + advisory)."""
    from ..understanding.grading.aggregation import grade_hybrid

    g = grade_hybrid(
        "Explain why recovering an equation from data is not discovering a law.",
        response, ["imposed library", "fit", "not a law", "system identification"],
        forbidden_elements=["discovered a law of nature", "proves the mechanism"])
    typer.echo(f"verdict: {g.verdict.value}  score={g.score}  "
               f"can_reach_mastery={g.can_reach_mastery}")
    for r in g.reasons:
        typer.echo(f"  - {r}")


@learner_app.command("grader-benchmark")
def learner_grader_benchmark() -> None:
    """Run the grader calibration + adversarial audit."""
    from ..understanding.grading.audit import run as audit_run
    from ..understanding.grading.calibration import run as cal_run

    c = cal_run()
    typer.echo(f"calibration: agreement={c.agreement} FP={c.false_positives} "
               f"FN={c.false_negatives}")
    a = audit_run()
    typer.echo(f"adversarial: any_fooled={a.any_fooled} "
               f"({sum(1 for x in a.attacks if not x.fooled)}/{len(a.attacks)} resisted)")


# --- Scientific Reliability (Sprint 11) -----------------------------------

@reliability_app.command("audit-writes")
def reliability_audit_writes() -> None:
    """Show the write-surface inventory summary."""
    typer.echo("See docs/security/write_surface_inventory.md")
    typer.echo("Protected: World Model, Discovery, Understanding, Negative Registry, "
               "Literature, Publication candidates")
    typer.echo("Admin-only: ledger/provenance (append-only). No central path LEGACY_UNPROTECTED.")


@reliability_app.command("evidence-dependencies")
def reliability_evidence() -> None:
    """Demo the evidence dependency graph (3 same-dataset + 1 independent)."""
    from ..reliability.evidence import DependencyGraph, Evidence, dependency_aware_support

    g = DependencyGraph()
    for i in range(3):
        g.add(Evidence(id=f"e{i}", dataset="D1", pipeline="P1"))
    g.add(Evidence(id="ind", dataset="D2"))
    s = dependency_aware_support(g)
    typer.echo(f"items={s['n_items']} independent_groups={s['n_independent_groups']} "
               f"naive={s['naive_support']} dependency_aware={s['dependency_aware_support']}")


@reliability_app.command("replication")
def reliability_replication() -> None:
    """Show replication levels and which count as independent."""
    from ..reliability.evidence import INDEPENDENT_REPLICATION_LEVELS, ReplicationLevel

    for lvl in ReplicationLevel:
        indep = "independent" if lvl in INDEPENDENT_REPLICATION_LEVELS else "NOT independent"
        typer.echo(f"  {lvl.value}: {indep}")


@reliability_app.command("calibration-report")
def reliability_calibration_report() -> None:
    """Demo calibration metrics on overconfident predictions."""
    from ..reliability.calibration import CalibrationObservation, CalibrationRegistry

    reg = CalibrationRegistry()
    for i in range(12):
        reg.record(CalibrationObservation("m", "probability", predicted_probability=0.9,
                                          actual_outcome=(i % 5 == 0)))
    typer.echo(f"probability metrics: {reg.probability_metrics()}")


@reliability_app.command("red-team")
def reliability_red_team() -> None:
    """Run the scientific red team."""
    from ..reliability.red_team import run_red_team

    r = run_red_team().as_dict()
    typer.echo(f"red team {r['version']}: {r['detected']}/{r['n']} detected")
    if r["missed"]:
        typer.echo(f"  MISSED: {r['missed']}")
    for cat, s in r["by_category"].items():
        typer.echo(f"  {cat}: {s['detected']}/{s['total']}")


@reliability_app.command("mutate")
def reliability_mutate() -> None:
    """Run scientific mutation testing."""
    from ..reliability.mutation import run_mutation_testing

    m = run_mutation_testing().as_dict()
    typer.echo(f"mutations: {m['caught']}/{m['n']} caught")
    if m["survived"]:
        typer.echo(f"  SURVIVED: {m['survived']}")


@reliability_app.command("scorecard")
def reliability_scorecard() -> None:
    """Build and print a Scientific Reliability Card."""
    from ..reliability.engine import build_card

    card = build_card().as_dict()
    for name, d in card["dimensions"].items():
        m = d["measurement"]
        typer.echo(f"  {name}: {'n/a' if m is None else round(m, 3)} "
                   f"(n={d['sample']}, thr={d['threshold']})")


@reliability_app.command("readiness")
def reliability_readiness() -> None:
    """Show the readiness ladder (DISCOVERY_CONFIRMED does not exist)."""
    from ..reliability.engine import readiness_levels

    for lvl in readiness_levels():
        typer.echo(f"  {lvl}")
    typer.echo("NOTE: DISCOVERY_CONFIRMED is intentionally not implemented.")


@reliability_app.command("gauntlet")
def reliability_gauntlet() -> None:
    """Run the Scientific Reliability Gauntlet (10 tracks)."""
    from ..benchmarks.reliability_gauntlet import run_gauntlet

    r = run_gauntlet()
    for name, t in r["tracks"].items():
        typer.echo(f"  {'✓' if t['passed'] else '✗'} {name}")
    typer.echo(f"{r['passed']}/{r['n']} tracks passed; all_passed={r['all_passed']}")


@gate_app.command("token")
def gate_token(action: str = typer.Argument("demo"),
               inspect: bool = typer.Option(False, "--inspect")) -> None:
    """Issue and validate a demo mutation token."""
    from ..epistemic_gate.tokens import TokenRegistry

    reg = TokenRegistry()
    tok = reg.issue(action=action, project_id="demo", artifact_ids=("a1",))
    typer.echo(f"issued token {tok.token_id} (action={action}, expires {tok.expires_at})")
    if inspect:
        typer.echo(f"  {tok.as_dict()}")
    reg.validate(tok, action=action, project_id="demo")
    reg.spend(tok)
    typer.echo(f"validated + spent; metrics={reg.metrics()}")


@gate_app.command("full-bypass-test")
def gate_full_bypass_test() -> None:
    """Run the concurrent bypass track (threads without a valid context)."""
    from ..benchmarks.reliability_gauntlet import track10_concurrent_bypass

    r = track10_concurrent_bypass()
    typer.echo(f"concurrent bypass: {r['blocked']}/{r['attempts']} blocked "
               f"(passed={r['passed']})")


@publication_app.command("candidate")
def publication_candidate() -> None:
    """Prepare a demo publication candidate (never publishes)."""
    from ..reliability.engine import run_reliability

    r = run_reliability("demo", reproducibility=0.9, calibration=0.8,
                        evidence_independence=0.7, human_understanding=0.9,
                        provenance=0.9, externally_validated=False)
    pc = r["publication_candidate"]
    typer.echo(f"readiness: {pc['readiness']}  auto-publish: {pc['can_publish_automatically']}")
    typer.echo(f"blockers: {r['blockers']}")


@publication_app.command("readiness")
def publication_readiness() -> None:
    """Show the readiness ceiling."""
    typer.echo("Ceiling: READY_FOR_HUMAN_SCIENTIFIC_REVIEW (never auto-publishes; "
               "DISCOVERY_CONFIRMED does not exist).")


@publication_app.command("dossier")
def publication_dossier(
    claim: str = typer.Option("damped oscillation recovered as ẋ=v, v̇=−4x−0.5v"),
    ready: bool = typer.Option(True, help="build a review-ready dossier"),
) -> None:
    """Assemble a review dossier (evidence + reliability + limitations + disclaimers)."""
    from ..publication.dossier import DossierEvidence
    from ..publication.engine import build_dossier

    d = build_dossier(
        "cli", claim, externally_validated=ready,
        reproducibility=0.9 if ready else 0.4,
        supporting=[DossierEvidence("e1", "clean recovery", "supporting")],
        counter=[DossierEvidence("c1", "noise degrades fit", "counter")],
        limitations=["computational only", "polynomial library imposed"])
    typer.echo(f"dossier {d.id}: readiness={d.readiness} "
               f"independent_support={d.independent_support_count()}")
    typer.echo(f"  comprehension={d.comprehension_status} gate={d.gate_status}")
    for x in d.disclaimers()[:3]:
        typer.echo(f"  · {x}")


@publication_app.command("export")
def publication_export(
    reviewer: str = typer.Option(..., help="the human reviewer (not ACERO)"),
    out: str = typer.Option("", help="output directory"),
) -> None:
    """Build → review → gated LOCAL export (never publishes)."""
    from ..publication.dossier import DossierEvidence
    from ..publication.engine import build_dossier
    from ..publication.export import ExportBlocked, export_dossier
    from ..publication.review import HumanReviewSession, ReviewDecision

    d = build_dossier("cli", "damped oscillation recovered", externally_validated=True,
                      supporting=[DossierEvidence("e1", "clean recovery", "supporting")],
                      counter=[DossierEvidence("c1", "noise degrades fit", "counter")],
                      limitations=["computational only"])
    r = HumanReviewSession(dossier_id=d.id, reviewer=reviewer, comprehension_ok=True)
    for s in ("central_claim", "main_evidence", "main_counter_evidence", "limitations",
              "reliability", "what_remains_to_validate_externally"):
        r.acknowledge(s)
    try:
        r.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"review not approved: {exc}")
        raise typer.Exit(1) from exc
    path = out or str(repo_root() / "research" / "artifacts" / "review_export")
    try:
        res = export_dossier(d, r, path)
        typer.echo(f"exported LOCALLY to {res['dir']} (auto_published={res['auto_published']})")
    except ExportBlocked as exc:
        typer.echo(f"export BLOCKED: {exc.blockers}")
        raise typer.Exit(1) from exc


@publication_app.command("gauntlet")
def publication_gauntlet() -> None:
    """Run the Human Scientific Review Gauntlet."""
    import tempfile

    from ..benchmarks.review_gauntlet import run_review_gauntlet

    with tempfile.TemporaryDirectory() as td:
        r = run_review_gauntlet(td)
    for name, c in r["cases"].items():
        typer.echo(f"  {'✓' if c['passed'] else '✗'} {name}")
    typer.echo(f"{r['passed']}/{r['n']} cases passed; all_passed={r['all_passed']}")


# --- Secret management (Sprint 14) ----------------------------------------

@secrets_app.command("init")
def secrets_init() -> None:
    """Generate a fresh HMAC secret to export (never stored in Git; shown once)."""
    from ..runtime.secrets import generate_secret

    key_id, hex_secret = generate_secret()
    typer.echo("Add these to your environment (do NOT commit them):")
    typer.echo(f"  export ACERO_HMAC_KEY_ID={key_id}")
    typer.echo(f"  export ACERO_HMAC_SECRET={hex_secret}")
    typer.echo("For production: also set ACERO_ENV=production (refuses to sign without a secret).")


@secrets_app.command("rotate")
def secrets_rotate() -> None:
    """Generate a replacement secret + key id (rotation). Old tokens stop verifying."""
    from ..runtime.secrets import generate_secret

    key_id, hex_secret = generate_secret()
    typer.echo("Rotate by exporting the new values (tokens signed with the old key will fail):")
    typer.echo(f"  export ACERO_HMAC_KEY_ID={key_id}")
    typer.echo(f"  export ACERO_HMAC_SECRET={hex_secret}")


@secrets_app.command("status")
def secrets_status() -> None:
    """Show secret mode + key id (never the secret itself)."""
    from ..runtime.secrets import secret_status

    s = secret_status()
    typer.echo(f"mode: {s['mode']} · key_id: {s['key_id']} · configured: {s['configured']}")
    if not s["configured"] and s["mode"] == "production":
        typer.echo("  WARNING: production mode without a configured secret — signing will refuse.")


# --- Worker runtime (Sprint 14) -------------------------------------------

@worker_app.command("start")
def worker_start(
    max_tasks: int = typer.Option(50, help="max tasks to drain this invocation"),
) -> None:
    """Drain the persistent research queue (claims → runs registered handlers → completes).

    This drains once and exits (a long-running daemon needs an external process manager;
    call repeatedly or from a supervisor). A demo 'echo' handler is registered."""
    from ..runtime.queue import ResearchQueue
    from ..runtime.worker import Worker

    q = ResearchQueue(default_session_factory())
    w = Worker(q)
    w.register("echo", lambda payload, ckpt, hb: {"echo": payload})
    q.reap_expired()
    n = w.drain(max_tasks=max_tasks)
    typer.echo(f"worker {w.worker_id}: processed={w.processed} failed={w.failed} drained={n}")


@worker_app.command("status")
def worker_status() -> None:
    """Show the persistent queue state by status."""
    from ..runtime.store import RuntimeStore

    store = RuntimeStore(default_session_factory())
    by_status: dict[str, int] = {}
    for t in store.tasks():
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    typer.echo(f"queue: {by_status or 'empty'}")


@worker_app.command("enqueue")
def worker_enqueue(kind: str = typer.Argument("echo"),
                   note: str = typer.Option("hello", help="payload note")) -> None:
    """Enqueue a demo task (idempotent via a key)."""
    from ..core.ids import new_id
    from ..runtime.queue import ResearchQueue

    q = ResearchQueue(default_session_factory())
    tid = new_id("task")
    q.enqueue(tid, kind, payload={"note": note}, idempotency_key=f"cli-{note}")
    typer.echo(f"enqueued {tid} (kind={kind})")


@worker_app.command("stop")
def worker_stop() -> None:
    """Signal workers to stop (cooperative). This build drains synchronously, so this is a
    no-op marker; documented in the Sprint 14 report."""
    typer.echo("workers drain synchronously in this build; nothing to stop.")


@worker_app.command("chaos")
def worker_chaos() -> None:
    """Run the Persistent Runtime Chaos Gauntlet (12 fault scenarios)."""
    from ..benchmarks.chaos_gauntlet import run_chaos_gauntlet

    r = run_chaos_gauntlet()
    for name, c in r["cases"].items():
        typer.echo(f"  {'✓' if c['passed'] else '✗'} {name}")
    typer.echo(f"{r['passed']}/{r['n']} scenarios passed; all_passed={r['all_passed']}")


# --- Research Program OS (Sprint 16) --------------------------------------

def _program_engine():
    from ..program.engine import ProgramEngine
    _, _, store = _discovery()
    return ProgramEngine(store)


@program_app.command("create")
def program_create(
    mission: str = typer.Argument(...),
    domains: str = typer.Option("", help="comma-separated domains"),
    question: str = typer.Option("", help="central question"),
) -> None:
    """Create a research program."""
    pe = _program_engine()
    p = pe.create(mission, domains=[d.strip() for d in domains.split(",") if d.strip()],
                  central_question=question or None)
    typer.echo(f"program {p.id}: {p.mission[:60]} [{p.status.value}]")


@program_app.command("list")
def program_list() -> None:
    """List research programs."""
    pe = _program_engine()
    for p in pe.programs():
        typer.echo(f"  {p.id}: {p.mission[:55]} [{p.status.value}] "
                   f"({len(p.subprojects)} subprojects)")


@program_app.command("view")
def program_view(program_id: str = typer.Argument(...)) -> None:
    """Show a program's strategic view (questions, milestones, budget, retrospectives)."""
    pe = _program_engine()
    try:
        v = pe.strategic_view(program_id)
    except KeyError:
        typer.echo("program not found")
        raise typer.Exit(1) from None
    typer.echo(f"mission: {v['mission']} [{v['status']}]")
    typer.echo(f"questions: {v['questions_by_role']}")
    typer.echo(f"milestones: {v['milestones_done']}/{v['n_milestones']} · "
               f"retrospectives: {v['n_retrospectives']}")
    for res, b in v["budget"].items():
        if b["budget"]:
            typer.echo(f"  budget {res}: {b['used']}/{b['budget']} (remaining {b['remaining']})")


@program_app.command("prioritize")
def program_prioritize() -> None:
    """Demo multi-dimensional portfolio prioritization (no single opaque score)."""
    pe = _program_engine()
    pf = pe.prioritize({
        "proj_A": {"information_gain": 0.9, "feasibility": 0.8, "risk": 0.2,
                   "data_available": 0.9},
        "proj_B": {"information_gain": 0.4, "feasibility": 0.5, "risk": 0.7,
                   "data_available": 0.3}})
    for s in pf.ranked():
        typer.echo(f"  {s.project_id}: view={s.composite_view} dims={s.dimensions}")


# --- Database migrations (Sprint 22) --------------------------------------

@db_app.command("status")
def db_status() -> None:
    """Show the current migration revision and head."""
    from ..migrations import api

    c = api.check()
    typer.echo(f"current: {c['current']} · head: {c['head']} · status: {c['status']}")


@db_app.command("upgrade")
def db_upgrade(revision: str = typer.Argument("head")) -> None:
    """Upgrade the database to a revision (default head). Idempotent on a create_all DB."""
    from ..migrations import api

    typer.echo(f"upgraded to: {api.upgrade(revision=revision)}")


@db_app.command("downgrade")
def db_downgrade(revision: str = typer.Argument("base")) -> None:
    """Downgrade to a revision (default base = drop all)."""
    from ..migrations import api

    typer.echo(f"downgraded to: {api.downgrade(revision=revision)}")


@db_app.command("check")
def db_check() -> None:
    """Exit non-zero if the DB is not at head (CI/ops gate)."""
    from ..migrations import api

    c = api.check()
    typer.echo(f"{c['status']} (current={c['current']}, head={c['head']})")
    if not c["at_head"]:
        raise typer.Exit(1)


@db_app.command("history")
def db_history() -> None:
    """Show the migration history."""
    from ..migrations import api

    typer.echo(api.render_history() or "(no migrations)")


@db_app.command("stamp")
def db_stamp() -> None:
    """Stamp an existing (create_all) database at head without recreating tables."""
    from ..migrations import api

    api.stamp_head()
    typer.echo(f"stamped at head: {api.head()}")


# --- Collaboration & external review prep (Sprint 19) ---------------------

@collab_app.command("bundle")
def collab_bundle(out: str = typer.Option("", help="output directory"),
                  blind: str = typer.Option("OPEN_IDENTITY")) -> None:
    """Build a LOCAL external review bundle (never published)."""
    from ..collaboration.bundle import BlindMode, BundleError, build_bundle

    path = out or str(repo_root() / "research" / "artifacts" / "external_review_bundle")
    try:
        r = build_bundle(
            path, project="Stellar Variability & Regime Discovery",
            central_claims=[{"claim": "~11.2 yr cycle (data-level, no discovery)"}],
            methods="FFT periodogram + AR(1) red-noise surrogate + bootstrap CI",
            evidence_map=[{"id": "e1", "summary": "clean recovery"}],
            counterevidence=[{"id": "c1", "summary": "cycle length varies"}],
            limitations=["single dataset (SILSO)", "no instrument dependence assessed"],
            reliability_card={"adversarial_robustness": 1.0}, commit="2.0.0-rc2",
            licenses={"code": "MIT", "data": "public-domain"}, blind=BlindMode(blind))
    except BundleError as exc:
        typer.echo(f"bundle BLOCKED: {exc}")
        raise typer.Exit(1) from exc
    typer.echo(f"bundle → {r['dir']} · files={r['n_files']} · blind={r['blind']} · "
               f"auto_published={r['auto_published']}")


@collab_app.command("questions")
def collab_questions(role: str = typer.Option("", help="reviewer role")) -> None:
    """Show the review questions (not just 'do you agree?')."""
    from ..collaboration.questions import questions_for

    for q in questions_for(role or None):
        typer.echo(f"  - {q}")


@collab_app.command("gauntlet")
def collab_gauntlet() -> None:
    """Run the External Review Preparation Gauntlet."""
    import tempfile

    from ..benchmarks.external_review_gauntlet import run_external_review_gauntlet

    _, _, store = _discovery()
    with tempfile.TemporaryDirectory() as td:
        r = run_external_review_gauntlet(td, store)
    for name, c in r["cases"].items():
        typer.echo(f"  {'✓' if c['passed'] else '✗'} {name}")
    typer.echo(f"{r['passed']}/{r['n']} cases passed; all_passed={r['all_passed']}")


# --- Scientific self-evaluation (Sprint 18) -------------------------------

@evaluation_app.command("run")
def evaluation_run(benchmark: str = typer.Argument("", help="one benchmark, or all")) -> None:
    """Run the benchmark suite (or one), compare vs the locked baseline, report regressions."""
    from ..selfeval import benchmarks as bm
    from ..selfeval.engine import run_evaluation

    if benchmark:
        r = bm.run_one(benchmark)
        typer.echo(f"{benchmark}: passed={r['passed']} metrics={r['metrics']} "
                   f"({r['duration_sec']}s) commit={r['commit']}")
        return
    r = run_evaluation()
    typer.echo(f"verdict: {r['verdict']} · version {r['version']} · commit {r['commit']}")
    for b, v in r["benchmarks"].items():
        typer.echo(f"  {'✓' if v['passed'] else '✗'} {b}: {v['metrics']} ({v['duration_sec']}s)")
    if r["regression"].get("has_regression"):
        typer.echo(f"  REGRESSIONS: {r['regression']['regressions']}")
    typer.echo(r["note"])


@evaluation_app.command("status")
def evaluation_status() -> None:
    """Show capability statuses (evidence-driven; no auto-promotion)."""
    from ..selfeval.engine import run_evaluation

    for c in run_evaluation()["capabilities"]:
        typer.echo(f"  [{c['status']}] {c['name']} ({c['domain']}) "
                   f"benchmarks={c['benchmarks']}")


@evaluation_app.command("history")
def evaluation_history() -> None:
    """Show the locked baselines available for comparison."""
    from ..core.config import repo_root

    d = repo_root() / "evaluation" / "baselines"
    versions = sorted(p.name for p in d.iterdir()) if d.exists() else []
    typer.echo(f"locked baselines: {versions or 'none'}")


@evaluation_app.command("lock-baseline")
def evaluation_lock_baseline(
    version: str = typer.Argument("v2.0.0-rc1"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Run all benchmarks and lock them as the signed baseline for a version."""
    from ..selfeval.baseline import BaselineError
    from ..selfeval.engine import lock_baseline

    try:
        r = lock_baseline(version, force=force)
    except BaselineError as exc:
        typer.echo(f"refused: {exc}")
        raise typer.Exit(1) from exc
    typer.echo(f"baseline locked: {version} → {r['path']} (hash {r['hash'][:16]})")


@evaluation_app.command("failures")
def evaluation_failures() -> None:
    """Seed + list the failure memory by category."""
    from ..selfeval.failures import FailureMemory

    _, _, store = _discovery()
    fm = FailureMemory(store)
    fm.seed()
    typer.echo(f"failure memory by category: {fm.by_category()}")
    missing = fm.without_regression_test()
    if missing:
        typer.echo(f"  FIXED without regression test: {missing}")


# --- Backup / restore (Sprint 20) -----------------------------------------

@backup_app.command("create")
def backup_create(out: str = typer.Option("", help="backup directory")) -> None:
    """Create a local, hashed backup of the ACERO database."""
    from ..release import backup

    path = out or str(repo_root() / "backups" / "latest")
    m = backup.create(path)
    typer.echo(f"backup created at {path} · files={list(m['files'])} · "
               f"schema=v{m['schema_version']} (local_only)")


@backup_app.command("verify")
def backup_verify(path: str = typer.Argument(...)) -> None:
    """Verify a backup's integrity against its manifest."""
    from ..release import backup

    r = backup.verify(path)
    typer.echo(f"ok={r['ok']} failures={r['failures']} "
               f"version={r['acero_version']} schema=v{r['schema_version']}")
    if not r["ok"]:
        raise typer.Exit(1)


@backup_app.command("restore")
def backup_restore(path: str = typer.Argument(...)) -> None:
    """Restore the database from a VERIFIED backup (refuses if verification fails)."""
    from ..release import backup

    try:
        r = backup.restore(path)
    except backup.BackupError as exc:
        typer.echo(f"restore BLOCKED: {exc}")
        raise typer.Exit(1) from exc
    typer.echo(f"restored={r['restored']} → {r['target']} (version {r['acero_version']})")


# --- Release candidate (Sprint 20) ----------------------------------------

@release_app.command("manifest")
def release_manifest(write: bool = typer.Option(False, "--write", help="write to docs/releases")) -> None:
    """Print (or write) the release manifest."""
    from ..release.manifest import build_manifest, write_manifest

    m = build_manifest()
    typer.echo(f"{m['name']} {m['version']} · commit {m['commit']} · branch {m['branch']}")
    typer.echo(f"  packages={m['n_packages']} · gate_rules={m['gate_rules']} · "
               f"schema=v{m['schema_version']}")
    typer.echo(f"  auto_publication={m['security']['auto_publication']} · "
               f"benchmarks={len(m['benchmarks'])}")
    typer.echo(f"  known_issues: {len(m['known_issues'])}")
    if write:
        typer.echo(f"written: {write_manifest()}")


@release_app.command("accept")
def release_accept() -> None:
    """Run FINAL ACCEPTANCE (all gauntlets). Reports; never approves the release itself."""
    from ..release.manifest import final_acceptance

    r = final_acceptance()
    for name, g in r["gauntlets"].items():
        typer.echo(f"  {'✓' if g['all_passed'] else '✗'} {name}: {g['detail']}")
    typer.echo(f"verdict: {r['verdict']}")
    typer.echo(r["note"])
    if not r["all_gauntlets_passed"]:
        raise typer.Exit(1)


# --- Executed research studies (Sprint 17) --------------------------------

@studies_app.command("stellar-variability")
def studies_stellar_variability(
    surrogates: int = typer.Option(150, help="AR(1) red-noise surrogates for significance"),
) -> None:
    """Run the real astronomy program on the public SILSO sunspot series (no discovery)."""
    from ..studies.stellar_variability import run_program

    r = run_program(n_surrogates=surrogates)
    a = r["analysis"]
    typer.echo(f"Program: {r['program']}")
    typer.echo(f"dataset: n={r['dataset']['n']} sha={r['dataset']['sha256'][:12]} "
               f"({r['dataset']['reference']})")
    typer.echo(f"dominant period: {a['dominant_period_years']} yr · class: {a['classification']}")
    b = a["bootstrap_period"]
    typer.echo(f"cycle length: {b.get('median_years')} yr, 95% CI {b.get('ci95_years')} "
               f"({b.get('n_cycles')} cycles)")
    s = a["surrogate"]
    typer.echo(f"significance vs {s['null_model']}: p={s['p_value']} "
               f"(significant={s['significant_vs_null']})")
    typer.echo(f"low-activity regimes (Dalton-like): {a['low_activity_decades'][:4]}")
    typer.echo("hypotheses:")
    for h, v in r["hypotheses"].items():
        typer.echo(f"  {h}: {v}")
    typer.echo("CANNOT conclude:")
    for c in r["cannot_conclude"]:
        typer.echo(f"  · {c}")
    typer.echo("External review PENDING. No discovery is claimed.")


# --- Unified Research Portal (Sprint 15) ----------------------------------

@app.command("portal")
def portal(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve the unified research portal (local web app at /portal)."""
    import os

    import uvicorn

    from ..portal.auth import UserStore
    # honor the PORT env var (12-factor / preview harnesses) over the default
    port = int(os.environ.get("PORT", port))
    if not UserStore().usernames():
        typer.secho("No portal users yet. Create one first: acero portal-user add <name>",
                    fg=typer.colors.YELLOW)
    typer.echo(f"ACERO portal → http://{host}:{port}/portal/  (local-first; never publishes)")
    uvicorn.run("acero.api.app:create_app", host=host, port=port, factory=True)


@app.command("portal-user")
def portal_user(action: str, username: str = "", overwrite: bool = False) -> None:
    """Manage local portal users (add|list). Passwords are read from stdin, hashed."""
    import getpass

    from ..portal.auth import UserStore
    store = UserStore()
    if action == "list":
        for u in store.usernames():
            typer.echo(u)
        if not store.usernames():
            typer.echo("(no users)")
        return
    if action == "add":
        if not username:
            typer.secho("username required", fg=typer.colors.RED)
            raise typer.Exit(1)
        pw = getpass.getpass("New password (min 8 chars): ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw != pw2:
            typer.secho("passwords do not match", fg=typer.colors.RED)
            raise typer.Exit(1)
        try:
            store.create_user(username, pw, overwrite=overwrite)
        except ValueError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(1) from exc
        typer.secho(f"user '{username}' created (password hashed, never stored plain)",
                    fg=typer.colors.GREEN)
        return
    typer.secho("unknown action; use add|list", fg=typer.colors.RED)
    raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print the ACERO version."""
    typer.echo(__version__)


@app.command()
def demo(what: str = typer.Argument("full")) -> None:
    """Run an end-to-end research demo (`acero demo full`) — local, no publication."""
    if what != "full":
        typer.secho("only 'full' is supported", fg=typer.colors.RED)
        raise typer.Exit(1)
    from .demo import run_full_demo
    for line in run_full_demo():
        typer.echo(line)


@app.command()
def acceptance() -> None:
    """Run the ACERO 2.1.0-rc1 acceptance matrix (reports; a human decides)."""
    from ..release.acceptance import acceptance_matrix
    m = acceptance_matrix()
    for name, row in m["rows"].items():
        color = typer.colors.GREEN if row["status"] == "PASS" else typer.colors.RED
        typer.secho(f"  {name:26s} {row['status']:8s} [{row['verified_by']}] {row['evidence']}",
                    fg=color)
    typer.secho(f"\n{m['verdict']} — {m['n_pass']}/{m['n']} pass; blockers: {m['blockers'] or 'none'}",
                fg=typer.colors.GREEN if m["all_pass"] else typer.colors.RED)


@app.command("production")
def production(action: str = typer.Argument("score")) -> None:
    """Production readiness: `acero production score|audit|report` (evidence-based)."""
    from ..production.audit import run_audit
    r = run_audit()
    s = r["score"]
    if action in ("score", "audit", "report"):
        typer.secho(f"ACERO PRODUCTION READINESS: {s['total']:.1f} / 100 "
                    f"(goal {s['goal']})",
                    fg=typer.colors.GREEN if s["total"] >= 95 else typer.colors.YELLOW)
        for k in sorted(s["category_points"]):
            typer.echo(f"  {k}: {s['category_points'][k]:.1f} / {s['max_by_category'][k]}"
                       + (f"   — {r['category_evidence'][k]}" if action == "report" else ""))
        if s["global_blockers"]:
            typer.secho("blockers: " + "; ".join(s["global_blockers"]), fg=typer.colors.RED)
        typer.secho(f"≥95 requires (still missing): {s['rule10_missing']}",
                    fg=typer.colors.YELLOW)
        for n in s["applied_notes"]:
            typer.echo(f"  · {n}")
    else:
        typer.secho("actions: score|audit|report", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command("mesh")
def mesh(action: str = typer.Argument("sources"), arg: str = typer.Argument("")) -> None:
    """Scientific Knowledge Mesh: `acero mesh sources|health|lookup <doi>|search <query>`."""
    from ..knowledge_mesh import mesh as m
    if action == "sources":
        for s in m.list_sources():
            typer.echo(f"  {s['source_id']:14s} {s['authority_level']:20s} "
                       f"{s['health_status']:8s} {s['canonical_domain']}")
    elif action == "health":
        r = m.health_report(live=True)
        for x in r["results"]:
            c = typer.colors.GREEN if x["ok"] else typer.colors.RED
            typer.secho(f"  {x['source_id']:14s} {str(x['http_status']):5s} {x['health_status']}", fg=c)
        typer.secho(f"verified {r['n_verified']}/{r['n_sources']}", fg=typer.colors.GREEN)
    elif action == "lookup":
        if not arg:
            typer.secho("provide a DOI", fg=typer.colors.RED)
            raise typer.Exit(1)
        r = m.lookup_doi(arg)
        if not r["found"]:
            typer.secho(f"not found in Crossref: {arg} (reported unverified, not invented)",
                        fg=typer.colors.YELLOW)
            return
        o = r["object"]
        typer.echo(f"  title:     {o['title']}")
        typer.echo(f"  type:      {o['object_type']}  |  review: {o['review_status']}")
        color = typer.colors.RED if o["integrity_status"] != "normal" else typer.colors.GREEN
        typer.secho(f"  integrity: {o['integrity_status']}", fg=color)
        typer.echo(f"  authors:   {', '.join(o['authors'][:5])}")
        typer.echo(f"  license:   {(o['license'] or {}).get('url')}")
        typer.echo(f"  url:       {o['canonical_url']}")
    elif action == "search":
        if not arg:
            typer.secho("provide a query", fg=typer.colors.RED)
            raise typer.Exit(1)
        r = m.search(arg, rows=5)
        typer.echo(f"query: {r['query']}  ·  sources: {r['sources_consulted']}  ·  n={r['n_results']}")
        for it in r["results"]:
            flag = "" if it["integrity_status"] == "normal" else f" [{it['integrity_status'].upper()}]"
            typer.echo(f"  - {it['type']}{flag} | {(it['title'] or '')[:64]} | {it['doi']}")
    else:
        typer.secho("actions: sources|health|lookup <doi>|search <query>", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command("security-audit")
def security_audit_cmd() -> None:
    """Run the release security audit."""
    from ..release.security_audit import security_audit
    a = security_audit()
    for c in a["checks"]:
        typer.secho(f"  {'OK ' if c['ok'] else 'BAD'} {c['check']:24s} {c['evidence']}",
                    fg=typer.colors.GREEN if c["ok"] else typer.colors.RED)
    typer.secho(f"\n{a['n_ok']}/{a['n']} ok; failures: {a['failures'] or 'none'}",
                fg=typer.colors.GREEN if a["all_ok"] else typer.colors.RED)


@science_app.command("simbench")
def science_simbench() -> None:
    """Run the Simulation & Recovery Bench on the reference naive t-test."""
    from ..science.simbench import evaluate, naive_ttest

    rep = evaluate(naive_ttest(), n_reps=200, n=200)
    for k, v in rep.summary().items():
        typer.echo(f"  {k}: {v}")
    typer.secho("apto para ASOCIACIÓN pero NO para causal (se deja engañar por "
                "confusión/lote) — el bench lo revela.", fg=typer.colors.YELLOW)


@science_app.command("states")
def science_states() -> None:
    """Show the scientific state ladder and ACERO's hard ceiling."""
    from ..science.states import ACERO_CEILING, ScientificState, is_external_state

    for s in ScientificState:
        mark = " <-- TOPE ACERO" if s is ACERO_CEILING else (
            "  (solo externo)" if is_external_state(s) else "")
        typer.echo(f"  {int(s):2d}  {s.name}{mark}")


@science_app.command("demo")
def science_demo() -> None:
    """Govern a toy result through the constitution (offline, deterministic)."""
    from ..science.claim_compiler import EvidenceProfile
    from ..science.constitution import GovernanceInput, StatisticalControls, govern
    from ..science.preregistration import Regime
    from ..science.states import StateEvidence

    gi = GovernanceInput(
        EvidenceProfile("metilación_cpgX", "parkinson", Regime.DISCOVERY),
        draft_text="la metilación demuestra que causa parkinson",  # over-claims!
        controls=StatisticalControls(effect_size=True, confidence_intervals=True),
        state_evidence=StateEvidence(hypothesis_formulated=True,
                                     executed_with_null_test=True))
    rep = govern(gi)
    typer.echo(f"claim permitido: {rep.allowed_claim}")
    typer.echo(f"estado ACERO: {rep.acero_state.name}")
    typer.echo(f"sobreafirmaciones: {rep.overclaims}")
    typer.echo(f"avanza: {rep.advance_permitted}  | razones: {rep.reasons}")


if __name__ == "__main__":  # pragma: no cover
    app()
