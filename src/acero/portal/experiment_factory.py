"""Experiment Factory — proposed experiments become EXECUTED experiments.

The gap this closes: most proposed experiments used to end as a "reproducible
plan". Now, when no hand-written ACERO analysis matches, the factory:

  1. PLAN (Codex): resolves which PUBLIC datasets the experiment needs
     (allowlisted scientific hosts only).
  2. FETCH (trusted code): downloads the data itself — the LLM never touches the
     network — recording URL, bytes and SHA-256 as verifiable provenance.
  3. CODEGEN (Codex): writes a self-contained Python analysis script that reads
     ./data/, applies the experiment's null controls, evaluates the
     discriminator, and prints one `RESULT_JSON: {...}` line.
  4. RUN (ACERO sandbox): executes the script with network DISABLED, CPU/RAM
     limits and static screening. Up to 2 repair rounds feed errors back to
     Codex.
  5. VALIDATE + PACKAGE: the result is schema-checked (verdict must be
     supports|refutes|inconclusive; missing null test downgrades to
     inconclusive) and everything (script, data, result, stdout, run.sh) is
     written to a reproducible artifact directory.

Epistemic rules preserved: the ANALYSIS CODE is AI-written and must be human
reviewed — results are candidates, never discoveries; failures and refutations
are reported honestly (a factory that can't produce a valid run returns an
error and the experiment stays a PLAN — it never fabricates numbers).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root

# --- data-host allowlist (scientific, public) --------------------------------
DATA_HOST_ALLOWLIST = {
    # NASA / astronomy
    "exoplanetarchive.ipac.caltech.edu", "archive.stsci.edu", "mast.stsci.edu",
    "lambda.gsfc.nasa.gov", "heasarc.gsfc.nasa.gov", "irsa.ipac.caltech.edu",
    "data.giss.nasa.gov", "ssd.jpl.nasa.gov", "cmb.wintherscoming.no",
    # ESA
    "pla.esac.esa.int", "gea.esac.esa.int", "www.cosmos.esa.int",
    # observatories / archives
    "www.sidc.be", "sidc.be", "cdsarc.u-strasbg.fr", "vizier.u-strasbg.fr",
    "cdsarc.cds.unistra.fr", "www.gw-openscience.org", "gwosc.org",
    # general open science
    "zenodo.org", "export.arxiv.org", "arxiv.org", "api.openalex.org",
    "raw.githubusercontent.com", "ftp.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov",
}

MAX_DOWNLOAD_BYTES = 120 * 1024 * 1024      # 120 MB per file
FETCH_TIMEOUT = 180.0
SANDBOX_TIMEOUT = 150                        # analysis wall-clock (s)
SANDBOX_MEMORY_MB = 2048
MAX_REPAIRS = 2

_UA = "ACERO-experiment-factory/0.1 (mailto:merari.jafet@gmail.com)"
_RESULT_RE = re.compile(r"^RESULT_JSON:\s*(\{.*\})\s*$", re.MULTILINE)
_VERDICTS = {"supports", "refutes", "inconclusive"}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "data_urls": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "filename": {"type": "string"},
                "what": {"type": "string"},
            },
            "required": ["url", "filename", "what"],
            "additionalProperties": False}},
        "analysis_outline": {"type": "string"},
    },
    "required": ["data_urls", "analysis_outline"],
    "additionalProperties": False,
}


def artifacts_root() -> Path:
    env = os.environ.get("ACERO_EXPERIMENT_ARTIFACTS", "").strip()
    return Path(env) if env else repo_root() / "research" / "artifacts" / "experiments"


def _host_allowed(url: str) -> bool:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    if not host:
        return False
    extra = {h.strip().lower()
             for h in os.environ.get("ACERO_DATA_HOSTS_EXTRA", "").split(",") if h.strip()}
    allowed = {h.lower() for h in DATA_HOST_ALLOWLIST} | extra
    return host in allowed or any(host.endswith("." + a) for a in allowed)


def fetch_data(urls: list[dict[str, Any]], dest: Path, *,
               timeout: float = FETCH_TIMEOUT,
               max_bytes: int = MAX_DOWNLOAD_BYTES) -> list[dict[str, Any]]:
    """Trusted downloader: allowlisted hosts only; records verifiable provenance."""
    dest.mkdir(parents=True, exist_ok=True)
    prov: list[dict[str, Any]] = []
    for spec in urls:
        url = str(spec.get("url", "")).strip()
        name = re.sub(r"[^A-Za-z0-9._-]", "_", str(spec.get("filename") or "data.bin"))[:80]
        if not url.lower().startswith("https://"):
            raise ValueError(f"solo HTTPS permitido: {url[:80]}")
        if not _host_allowed(url):
            raise ValueError(f"host fuera del allowlist científico: {url[:100]}")
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        h = hashlib.sha256()
        n = 0
        path = dest / name
        with urllib.request.urlopen(req, timeout=timeout) as r, open(path, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                n += len(chunk)
                if n > max_bytes:
                    raise ValueError(f"descarga excede {max_bytes} bytes: {url[:80]}")
                h.update(chunk)
                f.write(chunk)
        if n == 0:
            raise ValueError(f"descarga vacía: {url[:80]}")
        prov.append({"url": url, "filename": name, "bytes": n,
                     "sha256": h.hexdigest(), "what": spec.get("what", ""),
                     "fetched_at": now_iso()})
    return prov


def _head_preview(path: Path, chars: int = 500) -> str:
    try:
        raw = path.read_bytes()[: chars * 4]
        txt = raw.decode("utf-8", "replace")
        return txt[:chars]
    except Exception:  # noqa: BLE001
        return "(binario)"


# --- Codex steps --------------------------------------------------------------

def _codex():
    from ..llm.providers import CodexCliProvider
    prov = CodexCliProvider(timeout_sec=240)
    if not prov.available():
        raise RuntimeError("codex unavailable")
    return prov


def default_plan(exp: dict[str, Any], hyp: dict[str, Any], domain: str) -> dict[str, Any]:
    """Ask Codex which public datasets the experiment needs (may be none)."""
    mt = exp.get("method_type", "")
    prov = _codex()
    allow = ", ".join(sorted(DATA_HOST_ALLOWLIST))
    out = prov.complete_json(
        f"Dominio: {domain}. Experimento: «{exp.get('title','')}». "
        f"Qué: {exp.get('what','')}. Cómo: {exp.get('how','')}. "
        f"Fuente de datos declarada: {exp.get('data_source','')}. "
        f"Tipo: {mt or 'desconocido'}.\n\n"
        "Si el experimento NECESITA datos externos, da data_urls con URLs HTTPS "
        "DIRECTAS a archivos/consultas públicas (CSV/TSV/FITS/JSON) SOLO de estos "
        f"hosts: {allow}. Prefiere consultas TAP/API que devuelvan CSV (p.ej. "
        "exoplanetarchive.ipac.caltech.edu/TAP/sync?query=...&format=csv, o "
        "www.sidc.be/SILSO/INFO/snmtotcsv.php). URLs REALES y verificables — si no "
        "conoces una URL exacta y pública, devuelve data_urls VACÍO y plantea el "
        "análisis como simulación/matemático autocontenido. NO inventes URLs. "
        "analysis_outline: 3-6 pasos del análisis con controles nulos.",
        PLAN_SCHEMA, temperature=0.2)
    return out


_CODE_RULES = (
    "REGLAS DEL SCRIPT (sandbox ACERO):\n"
    "- Python 3.12, UN solo archivo. Solo stdlib + numpy (scipy/astropy si es "
    "imprescindible). PROHIBIDO: red (socket/urllib/requests), subprocess, "
    "os.system, eval, exec, leer fuera de ./ .\n"
    "- Los datos ya están descargados en ./data/<filename> (si los hay).\n"
    "- Determinista: usa numpy.random.default_rng(0).\n"
    "- Implementa el análisis, los CONTROLES NULOS (surrogatos/shuffle/monte "
    "carlo según el experimento) y evalúa el DISCRIMINADOR.\n"
    "- Presupuesto: < 120 s de CPU, < 2 GB RAM.\n"
    "- Al FINAL imprime EXACTAMENTE una línea:\n"
    "  RESULT_JSON: {\"metrics\": {..números..}, \"null_test\": {\"description\": str, "
    "\"statistic\": num, \"threshold\": num, \"passed\": bool}, "
    "\"verdict\": \"supports|refutes|inconclusive\", \"verdict_reason\": str}\n"
    "- verdict se decide por el discriminador contra los nulos; si los datos no "
    "alcanzan, verdict=inconclusive y dilo en verdict_reason. NUNCA inventes "
    "números: todo métrico debe salir del cómputo.\n"
    "- Responde SOLO con el código Python (sin ``` ni explicación)."
)


def default_codegen(exp: dict[str, Any], hyp: dict[str, Any],
                    data_files: list[dict[str, Any]],
                    previews: dict[str, str],
                    feedback: str | None = None) -> str:
    prov = _codex()
    files_txt = "\n".join(
        f"- ./data/{d['filename']} ({d['bytes']} bytes, sha256 {d['sha256'][:12]}…): "
        f"{d.get('what','')}\n  PRIMEROS CARACTERES:\n  " +
        previews.get(d["filename"], "")[:400].replace("\n", "\n  ")
        for d in data_files) or "(sin archivos: análisis autocontenido)"
    fb = f"\n\nEL INTENTO ANTERIOR FALLÓ. Corrige la causa:\n{feedback[:1500]}\n" \
        if feedback else ""
    r = prov.complete(
        f"Escribe el script de análisis para este EXPERIMENTO.\n"
        f"Hipótesis: «{hyp.get('title','')}»\n"
        f"Experimento: {exp.get('title','')}\nQué mide: {exp.get('what','')}\n"
        f"Método: {exp.get('how','')}\nControles: {exp.get('controls','')}\n"
        f"Discriminador: {exp.get('discriminator','')}\n\n"
        f"ARCHIVOS DE DATOS:\n{files_txt}\n\n{_CODE_RULES}{fb}",
        temperature=0.2, max_tokens=4000)
    code = r.text.strip()
    # strip accidental markdown fences
    code = re.sub(r"^```(?:python)?\s*", "", code)
    code = re.sub(r"\s*```$", "", code)
    return code


# --- validation ----------------------------------------------------------------

def _parse_result(stdout: str) -> tuple[dict[str, Any] | None, str]:
    matches = list(_RESULT_RE.finditer(stdout or ""))
    if not matches:
        return None, "el script no imprimió la línea RESULT_JSON"
    m = matches[-1]                            # keep the LAST match
    try:
        res = json.loads(m.group(1))
    except Exception as exc:  # noqa: BLE001
        return None, f"RESULT_JSON inválido: {exc}"
    if not isinstance(res.get("metrics"), dict) or not res["metrics"]:
        return None, "RESULT_JSON sin metrics numéricas"
    if res.get("verdict") not in _VERDICTS:
        return None, f"verdict inválido: {res.get('verdict')!r}"
    if not str(res.get("verdict_reason", "")).strip():
        return None, "falta verdict_reason"
    nt = res.get("null_test")
    if not isinstance(nt, dict) or "passed" not in nt:
        # honesty rule: no null controls ⇒ the result cannot claim support
        if res["verdict"] == "supports":
            res["verdict"] = "inconclusive"
            res["verdict_reason"] = ("[degradado por ACERO: sin control nulo "
                                     "verificable] " + str(res.get("verdict_reason", "")))
        res["null_test"] = {"description": "ausente", "passed": None}
    return res, ""


# --- main entry ------------------------------------------------------------------

def run_generated(exp: dict[str, Any], hyp: dict[str, Any], *, domain: str = "",
                  plan: Callable[..., dict[str, Any]] | None = None,
                  codegen: Callable[..., str] | None = None,
                  fetch: Callable[..., list[dict[str, Any]]] | None = None,
                  max_repairs: int = MAX_REPAIRS) -> dict[str, Any]:
    """Full factory pipeline. Returns {ok, result?, error?, ...} — never fabricates."""
    from ..sandbox.runner import SubprocessRunner

    plan = plan or default_plan
    codegen = codegen or default_codegen
    fetch = fetch or fetch_data

    exp_id = exp.get("id") or "exp_unknown"
    workdir = artifacts_root() / exp_id
    data_dir = workdir / "data"
    workdir.mkdir(parents=True, exist_ok=True)

    # 1) plan: which public data does this need?
    try:
        p = plan(exp, hyp, domain)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "plan", "error": str(exc)[:300]}
    urls = list(p.get("data_urls") or [])

    # 2) trusted fetch with provenance
    provenance: list[dict[str, Any]] = []
    if urls:
        try:
            provenance = fetch(urls, data_dir)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "stage": "fetch", "error": str(exc)[:300]}
    if exp.get("method_type") == "download_data" and not provenance:
        return {"ok": False, "stage": "fetch",
                "error": "experimento download_data sin datos descargables verificables"}

    previews = {d["filename"]: _head_preview(data_dir / d["filename"])
                for d in provenance}

    # 3-4) codegen + sandboxed run + repair loop
    runner = SubprocessRunner()
    feedback: str | None = None
    attempts = 0
    code = ""
    sres = None
    result: dict[str, Any] | None = None
    why = ""
    while attempts <= max_repairs:
        attempts += 1
        try:
            code = codegen(exp, hyp, provenance, previews, feedback)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "stage": "codegen", "error": str(exc)[:300],
                    "attempts": attempts}
        sres = runner.run(code, workdir, timeout_sec=SANDBOX_TIMEOUT,
                          memory_mb=SANDBOX_MEMORY_MB, allow_network=False)
        if sres.status == "ok" and sres.exit_code == 0:
            result, why = _parse_result(sres.stdout)
            if result is not None:
                break
        feedback = (f"status={sres.status} exit={sres.exit_code}\n"
                    f"STDERR:\n{(sres.stderr or '')[-1200:]}\n"
                    f"STDOUT (cola):\n{(sres.stdout or '')[-600:]}\n"
                    + (f"VALIDACIÓN: {why}" if why else ""))
        result = None

    if result is None:
        (workdir / "last_attempt.py").write_text(code or "", encoding="utf-8")
        return {"ok": False, "stage": "run", "attempts": attempts,
                "error": (feedback or "sin resultado válido")[:400]}

    # 5) reproducible package
    (workdir / "script.py").write_text(code, encoding="utf-8")
    (workdir / "stdout.txt").write_text(sres.stdout if sres else "", encoding="utf-8")
    (workdir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    (workdir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (workdir / "run.sh").write_text(
        "#!/bin/sh\n# Reproducción: los datos de ./data/ tienen sha256 en "
        "provenance.json\npython3 -I script.py\n", encoding="utf-8")

    return {"ok": True, "result": result, "provenance": provenance,
            "attempts": attempts, "code_path": str(workdir / "script.py"),
            "artifacts_dir": str(workdir),
            "duration_sec": round(getattr(sres, "duration_sec", 0.0), 2),
            "generator": "codex+sandbox",
            "disclaimer": ("Análisis con CÓDIGO GENERADO POR IA ejecutado en sandbox "
                           "sobre datos con procedencia verificada. Candidato a "
                           "revisión humana del código; no es un descubrimiento.")}
