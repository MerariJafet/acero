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
import shutil
import time
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
    # general open science / repositories
    "zenodo.org", "export.arxiv.org", "arxiv.org", "api.openalex.org",
    "raw.githubusercontent.com", "ftp.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov",
    "api.figshare.com", "ndownloader.figshare.com", "figshare.com",
    "datadryad.org", "pubchem.ncbi.nlm.nih.gov", "www.ebi.ac.uk",
    "rest.uniprot.org", "data.rcsb.org", "files.rcsb.org",
    "dataverse.harvard.edu",
    # cloud open-data (public buckets over HTTPS)
    "s3.amazonaws.com", "storage.googleapis.com",
}

# tuned to a real workstation (this machine has 62GB RAM); all overridable by env
MAX_DOWNLOAD_BYTES = int(os.environ.get("ACERO_MAX_DOWNLOAD_MB", "2048")) * 1024 * 1024
# per-file wall-clock budget: kills runaway/unbounded downloads (e.g. an
# unbounded VizieR query) instead of hanging for tens of minutes.
DOWNLOAD_DEADLINE_SEC = int(os.environ.get("ACERO_DOWNLOAD_DEADLINE_SEC", "300"))
PRUNE_DATA_OVER_BYTES = int(os.environ.get("ACERO_PRUNE_OVER_MB", "50")) * 1024 * 1024
CACHE_CAP_BYTES = int(os.environ.get("ACERO_CACHE_CAP_GB", "20")) * 1024 * 1024 * 1024


def _enforce_cache_cap() -> None:
    """LRU-evict the shared download cache above CACHE_CAP_BYTES."""
    cache = artifacts_root() / "_cache"
    if not cache.exists():
        return
    files = sorted(cache.iterdir(), key=lambda f: f.stat().st_mtime)
    total = sum(f.stat().st_size for f in files)
    for f in files:
        if total <= CACHE_CAP_BYTES:
            break
        total -= f.stat().st_size
        f.unlink(missing_ok=True)
FETCH_TIMEOUT = 180.0
SANDBOX_TIMEOUT = int(os.environ.get("ACERO_SANDBOX_TIMEOUT", "600"))   # s
SANDBOX_MEMORY_MB = int(os.environ.get("ACERO_SANDBOX_MEMORY_MB", "12288"))  # 12GB
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
                "accession": {"type": "string"},   # GEO GSE…, repo ID (resolver builds URL)
                "filename": {"type": "string"},
                "what": {"type": "string"},
            },
            "required": ["url", "accession", "filename", "what"],
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
               max_bytes: int = MAX_DOWNLOAD_BYTES,
               cache_dir: Path | None = None) -> list[dict[str, Any]]:
    """Trusted downloader: allowlisted hosts only; records verifiable provenance.
    Downloads are CACHED by URL hash so re-runs and cross-checks reuse bytes."""
    dest.mkdir(parents=True, exist_ok=True)
    cache = cache_dir if cache_dir is not None else artifacts_root() / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    prov: list[dict[str, Any]] = []
    for spec in urls:
        url = str(spec.get("url", "")).strip()
        name = re.sub(r"[^A-Za-z0-9._-]", "_", str(spec.get("filename") or "data.bin"))[:80]
        if not url.lower().startswith("https://"):
            raise ValueError(f"solo HTTPS permitido: {url[:80]}")
        if not _host_allowed(url):
            raise ValueError(f"host fuera del allowlist científico: {url[:100]}")
        path = dest / name
        ckey = cache / hashlib.sha256(url.encode()).hexdigest()[:32]
        cached = ckey.exists() and ckey.stat().st_size > 0
        if cached:
            data = ckey.read_bytes()
            path.write_bytes(data)
            prov.append({"url": url, "filename": name, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(),
                         "what": spec.get("what", ""), "cached": True,
                         "fetched_at": now_iso()})
            continue
        # download with RETRIES on transient network errors (size/time-bounded)
        h = hashlib.sha256()
        n = 0
        last_exc: Exception | None = None
        for attempt in range(3):
            h = hashlib.sha256()
            n = 0
            deadline = time.monotonic() + DOWNLOAD_DEADLINE_SEC
            try:
                req = urllib.request.Request(url, headers={"User-Agent": _UA})
                with urllib.request.urlopen(req, timeout=timeout) as r, \
                        open(path, "wb") as f:
                    while True:
                        chunk = r.read(1 << 16)
                        if not chunk:
                            break
                        n += len(chunk)
                        if n > max_bytes:
                            raise ValueError(f"descarga excede {max_bytes} bytes "
                                             f"(¿consulta sin límite?): {url[:80]}")
                        if time.monotonic() > deadline:
                            raise ValueError(f"descarga excede el presupuesto de "
                                             f"{DOWNLOAD_DEADLINE_SEC}s: {url[:80]}")
                        h.update(chunk)
                        f.write(chunk)
                last_exc = None
                break
            except ValueError:
                raise                            # size/time limits are not retried
            except Exception as exc:  # noqa: BLE001 - transient network → retry
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
        if last_exc is not None:
            raise ValueError(f"descarga falló tras 3 intentos ({last_exc}): {url[:80]}")
        if n == 0:
            raise ValueError(f"descarga vacía: {url[:80]}")
        ckey.write_bytes(path.read_bytes())
        prov.append({"url": url, "filename": name, "bytes": n,
                     "sha256": h.hexdigest(), "what": spec.get("what", ""),
                     "cached": False, "fetched_at": now_iso()})
    # compressed files are extracted so the analysis script reads them directly
    for rec in prov:
        fn = rec["filename"]
        if fn.endswith(".gz"):
            plain = _gunzip(dest / fn)
            if plain:
                rec["decompressed_to"] = plain
        elif fn.endswith(".zip"):
            names = _unzip(dest / fn, dest)
            if names:
                rec["extracted"] = names[:20]
    return prov


def _unzip(path: Path, dest: Path) -> list[str]:
    """Extract a .zip bundle (e.g. a Dryad dataset) into dest; return file names."""
    import zipfile
    try:
        out = []
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir() or info.file_size > MAX_DOWNLOAD_BYTES:
                    continue
                safe = os.path.basename(info.filename)
                if not safe:
                    continue
                with z.open(info) as src, open(dest / safe, "wb") as f:
                    f.write(src.read())
                out.append(safe)
        return out
    except Exception:  # noqa: BLE001
        return []


def _gunzip(path: Path) -> str:
    """Decompress a .gz next to it; returns the new filename or ''."""
    import gzip
    try:
        out = path.with_suffix("")           # drop .gz
        with gzip.open(path, "rb") as g, open(out, "wb") as f:
            while True:
                chunk = g.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        return out.name
    except Exception:  # noqa: BLE001
        return ""


def _sanitize(s: str) -> str:
    """Strip NULs and control bytes so a data preview never breaks the Codex call
    (a real-data experiment failed with 'embedded null byte' on a binary CSV)."""
    if not s:
        return s
    s = s.replace("\x00", "")
    return "".join(c for c in s if c == "\n" or c == "\t" or ord(c) >= 32)


def _head_preview(path: Path, chars: int = 500) -> str:
    try:
        raw = path.read_bytes()[: chars * 4]
        txt = _sanitize(raw.decode("utf-8", "replace"))
        return txt[:chars] or "(sin texto legible — datos binarios/comprimidos)"
    except Exception:  # noqa: BLE001
        return "(binario)"


def _json_schema(path: Path) -> dict[str, Any]:
    """If the file is a JSON record-array, return its record keys + count.

    Recognizes a top-level list of objects, or a dict wrapping the records in a
    list value (ChEMBL: {"activities": [...]}, Zenodo: {"files": [...]}). Reads a
    bounded prefix so a huge file doesn't blow up memory.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(64)
        if head.strip()[:1] not in (b"{", b"["):
            return {}
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        return {}
    records: Any = None
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # the biggest list-of-objects value is the record set
        best: list[Any] = []
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and len(v) >= len(best):
                best = v
        records = best
    if not isinstance(records, list) or not records or not isinstance(records[0], dict):
        return {}
    cols = list(records[0].keys())[:60]
    return {"columns": cols, "n_rows": len(records), "delimiter": "json"}


def _schema(path: Path) -> dict[str, Any]:
    """Read a CSV/TSV/table's REAL columns + row count so codegen isn't blind.

    Feeding Codex the actual column names/count (not a 400-char blob) is what
    turns 'column not found' failures into working analyses. Skips GEO-style '!'
    comment lines. Handles JSON record-arrays (e.g. ChEMBL {"activities":[…]}) too.
    Returns {columns, n_rows, delimiter?} or {} if not introspectable.
    """
    js = _json_schema(path)
    if js:
        return js
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            header = ""
            for line in f:
                s = _sanitize(line).strip()
                if s and not s.startswith(("!", "#", "//")):
                    header = s
                    break
            if not header:
                return {}
            delim = "\t" if header.count("\t") > header.count(",") else ","
            cols = [c.strip().strip('"') for c in header.split(delim)][:60]
            if len(cols) < 2:
                return {}
            n = sum(1 for _ in f)            # remaining data rows (header consumed)
            return {"columns": cols, "n_rows": n, "delimiter": delim}
    except Exception:  # noqa: BLE001
        return {}


# --- Codex steps --------------------------------------------------------------

def _codex():
    from ..llm.providers import CodexCliProvider
    prov = CodexCliProvider(timeout_sec=240)
    if not prov.available():
        raise RuntimeError("codex unavailable")
    return prov


def default_plan(exp: dict[str, Any], hyp: dict[str, Any], domain: str,
                 feedback: str | None = None) -> dict[str, Any]:
    """Ask Codex which public datasets the experiment needs (may be none)."""
    mt = exp.get("method_type", "")
    prov = _codex()
    allow = ", ".join(sorted(DATA_HOST_ALLOWLIST))
    fb = f"\n\nINTENTO ANTERIOR: {feedback[:600]}\n" if feedback else ""
    out = prov.complete_json(fb +
        f"Dominio: {domain}. Experimento: «{exp.get('title','')}». "
        f"Qué: {exp.get('what','')}. Cómo: {exp.get('how','')}. "
        f"Fuente de datos declarada: {exp.get('data_source','')}. "
        f"Tipo: {mt or 'desconocido'}.\n\n"
        "Si el experimento NECESITA datos externos, da data_urls. Para CADA dataset "
        "provee: (a) accession — el ID de repositorio público si existe (p.ej. GEO "
        "'GSE111629'); ACERO construye la URL real de descarga desde la accesión — "
        "y/o (b) url — una URL HTTPS DIRECTA a un archivo/consulta pública "
        "(CSV/TSV/FITS/JSON/gz) SOLO de estos hosts: " + allow + ". Prefiere DATOS "
        "PROCESADOS y descargables (series matrix de GEO, TAP de NASA que devuelva "
        "CSV como exoplanetarchive.ipac.caltech.edu/TAP/sync?query=...&format=csv, "
        "SILSO www.sidc.be/SILSO/INFO/snmtotcsv.php). Si el dataset requiere ACCESO "
        "CONTROLADO (EGA/dbGaP) o son IDATs crudos pesados que no caben ni corren en "
        "una laptop, NO lo pongas como url descargable: deja data_urls VACÍO y "
        "reformula el análisis con datos PÚBLICOS PROCESADOS que sí bajen (p.ej. la "
        "matriz de betas del propio GEO) o como simulación/matemático autocontenido. "
        "accession vacío si no aplica; url vacío si solo das accession. NO inventes "
        "URLs. analysis_outline: 3-6 pasos con controles nulos.",
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
    "- Presupuesto AMPLIO (estación de trabajo): hasta ~10 min y ~10 GB RAM. Para "
    "matrices grandes (p.ej. 450K CpGs x cientos de muestras) usa numpy float32, "
    "lee por columnas/chunks si hace falta, y submuestrea sondas SOLO si no cabe "
    "(dilo en verdict_reason). Los .gz ya vienen DESCOMPRIMIDOS en ./data/.\n"
    "- Al FINAL imprime EXACTAMENTE una línea:\n"
    "  RESULT_JSON: {\"metrics\": {..números..}, \"null_test\": {\"description\": str, "
    "\"statistic\": num, \"threshold\": num, \"passed\": bool}, "
    "\"verdict\": \"supports|refutes|inconclusive\", \"verdict_reason\": str, "
    "\"anomalies\": [str]}\n"
    "- anomalies: lista (puede ir vacía) de DISCREPANCIAS INESPERADAS que el "
    "cómputo reveló — residuos raros, outliers, ventanas/subconjuntos que se "
    "comportan distinto, tensiones entre subconjuntos. Solo lo que los NÚMEROS "
    "muestran, con el valor concreto.\n"
    "- verdict se decide por el discriminador contra los nulos; si los datos no "
    "alcanzan, verdict=inconclusive y dilo en verdict_reason. NUNCA inventes "
    "números: todo métrico debe salir del cómputo.\n"
    "- Opcional: guarda gráficas PNG en ./out/ (crea el directorio).\n"
    "- Responde SOLO con el código Python (sin ``` ni explicación)."
)

_SECOND_IMPL = (
    "SEGUNDA IMPLEMENTACIÓN INDEPENDIENTE (verificación cruzada): implementa el "
    "MISMO experimento con un ENFOQUE ALGORÍTMICO DISTINTO al obvio (otra "
    "estimación espectral/estadística, otro esquema de surrogatos, otra "
    "parametrización). Mismo contrato RESULT_JSON y mismas claves en metrics "
    "para poder comparar. No copies la implementación típica.")


def default_codegen(exp: dict[str, Any], hyp: dict[str, Any],
                    data_files: list[dict[str, Any]],
                    previews: dict[str, str],
                    feedback: str | None = None) -> str:
    prov = _codex()

    def _fdesc(d: dict[str, Any]) -> str:
        name = d.get("decompressed_to") or d["filename"]
        head = previews.get(name, "")[:300].replace("\n", "\n  ")
        # REAL schema (columns + row count) beats a blind text preview
        if d.get("columns"):
            cols = ", ".join(d["columns"][:40])
            kind = ("ARRAY JSON de registros (cárgalo con json.load; los campos van "
                    "en cada objeto de la lista)" if d.get("fmt") == "json"
                    else "tabla")
            schema = (f"\n  ESQUEMA REAL — {kind} ({len(d['columns'])} campos, "
                      f"{d.get('n_rows','?')} registros): {cols}\n  Usa EXACTAMENTE "
                      f"estos nombres.")
        else:
            schema = ""
        return (f"- ./data/{name} ({d['bytes']} bytes, sha256 {d['sha256'][:12]}…"
                + (f", de {d['filename']}" if d.get('decompressed_to') else "")
                + (", extraído del zip" if d.get('extracted') else "")
                + f"): {d.get('what','')}{schema}\n  PRIMEROS CARACTERES:\n  {head}")
    files_txt = "\n".join(_fdesc(d) for d in data_files) \
        or "(sin archivos: análisis autocontenido)"
    multi = len(data_files) >= 2
    join_hint = (
        "\nCRUCE DE CATÁLOGOS (hay ≥2 datasets): el descubrimiento vive en UNIR "
        "datos que nadie combinó. Une los archivos por una CLAVE común (p.ej. "
        "'hostname'/nombre de la estrella anfitriona, o un ID compartido; "
        "normaliza mayúsculas/espacios). Reporta cuántas filas casaron y cuántas "
        "quedaron sin cruzar. La correlación/efecto que buscas SOLO aparece tras "
        "el join; contra el nulo, permuta la clave para romper la asociación.\n"
        if multi else "")
    geo = any("series_matrix" in (d.get("filename") or "") for d in data_files)
    geo_hint = (
        "\nFORMATO GEO series matrix: los FENOTIPOS/grupos están en líneas que "
        "empiezan con '!Sample_' — sobre todo '!Sample_characteristics_ch1' (p.ej. "
        "'disease state: Parkinson\\'s disease' vs 'control'/'PD-free'), "
        "'!Sample_title' y '!Sample_geo_accession'; cada una tiene UN valor por "
        "muestra separado por tabs, en el MISMO orden de columnas que la matriz de "
        "betas. Deriva caso/control buscando la subcadena de enfermedad en "
        "characteristics (case-insensitive); si no hay controles mapeados, revisa "
        "qué línea/característica realmente codifica el grupo antes de rendirte. "
        "Alinea muestras por el ID de columna (GSM…) entre metadatos y matriz.\n"
        if geo else "")
    fb = f"\n\nEL INTENTO ANTERIOR FALLÓ. Corrige la causa:\n{feedback[:1500]}\n" \
        if feedback else ""
    from .playbook import brief
    prompt = (
        brief(900) + "\n\n---\n\n"
        f"Escribe el script de análisis para este EXPERIMENTO.\n"
        f"Hipótesis: «{hyp.get('title','')}»\n"
        f"Experimento: {exp.get('title','')}\nQué mide: {exp.get('what','')}\n"
        f"Método: {exp.get('how','')}\nControles: {exp.get('controls','')}\n"
        f"Discriminador: {exp.get('discriminator','')}\n\n"
        f"ARCHIVOS DE DATOS:\n{files_txt}\n{join_hint}{geo_hint}\n{_CODE_RULES}{fb}")
    r = prov.complete(_sanitize(prompt), temperature=0.2, max_tokens=4000)
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
    an = res.get("anomalies")
    res["anomalies"] = [str(a)[:250] for a in an[:5]] if isinstance(an, list) else []
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

def _compare_results(a: dict[str, Any], b: dict[str, Any],
                     rel_tol: float = 0.15) -> tuple[bool, str]:
    """Two independent implementations must agree: same verdict AND shared
    numeric metrics within rel_tol. Honest disagreement → not agreed."""
    if b.get("verdict") != a.get("verdict"):
        return False, (f"veredictos difieren: {a.get('verdict')} vs "
                       f"{b.get('verdict')}")
    ma, mb = a.get("metrics") or {}, b.get("metrics") or {}
    shared = [k for k in ma if k in mb
              and isinstance(ma[k], (int, float)) and isinstance(mb[k], (int, float))]
    if not shared:
        return False, "sin métricas comparables entre implementaciones"
    bad = []
    for k in shared:
        va, vb = float(ma[k]), float(mb[k])
        denom = max(abs(va), abs(vb), 1e-12)
        if abs(va - vb) / denom > rel_tol:
            bad.append(f"{k}: {va:.4g} vs {vb:.4g}")
    if bad:
        return False, "métricas divergentes: " + "; ".join(bad[:4])
    return True, f"{len(shared)} métricas coinciden (tol {int(rel_tol*100)}%)"


def run_generated(exp: dict[str, Any], hyp: dict[str, Any], *, domain: str = "",
                  plan: Callable[..., dict[str, Any]] | None = None,
                  codegen: Callable[..., str] | None = None,
                  fetch: Callable[..., list[dict[str, Any]]] | None = None,
                  max_repairs: int = MAX_REPAIRS,
                  verify_supports: bool = True) -> dict[str, Any]:
    """Full factory pipeline. Returns {ok, result?, error?, ...} — never fabricates."""
    from ..sandbox.runner import SubprocessRunner

    plan = plan or default_plan
    codegen = codegen or default_codegen
    fetch = fetch or fetch_data

    exp_id = exp.get("id") or "exp_unknown"
    workdir = artifacts_root() / exp_id
    data_dir = workdir / "data"
    # start every run with a clean data dir so stale downloads from a previous
    # run (possibly a different domain) can never leak into this experiment
    shutil.rmtree(data_dir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)

    # 1-2) plan → trusted fetch; on fetch failure RE-PLAN with alternatives (2 rounds)
    provenance: list[dict[str, Any]] = []
    plan_fb: str | None = None
    fetch_err = ""
    for _round in range(2):
        try:
            if plan_fb is None:
                p = plan(exp, hyp, domain)
            else:
                try:
                    p = plan(exp, hyp, domain, feedback=plan_fb)
                except TypeError:              # injected planners may not take feedback
                    p = plan(exp, hyp, domain)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "stage": "plan", "error": str(exc)[:300]}
        # resolve dataset ACCESSIONS (e.g. GEO GSE…) into real download URLs;
        # download_data experiments also pull the real DATA matrix from /suppl/
        try:
            from .data_resolver import enrich_plan_urls
            p = enrich_plan_urls(
                p, want_data=(exp.get("method_type") == "download_data"),
                domain=domain)
        except Exception:  # noqa: BLE001 - resolver is best-effort
            pass
        urls = list(p.get("data_urls") or [])
        if not urls:
            fetch_err = ""            # re-plan chose a self-contained analysis
            break
        try:
            provenance = fetch(urls, data_dir)
            fetch_err = ""
            break
        except Exception as exc:  # noqa: BLE001
            fetch_err = str(exc)[:300]
            plan_fb = (f"Estas URLs FALLARON ({fetch_err}). Propón un dataset "
                       f"ALTERNATIVO público (otro host del allowlist u otra "
                       f"consulta), o data_urls vacío si el análisis puede ser "
                       f"autocontenido. URLs fallidas: "
                       + "; ".join(str(u.get('url', ''))[:90] for u in urls))
    if fetch_err and not provenance:
        return {"ok": False, "stage": "fetch", "error": fetch_err}
    if exp.get("method_type") == "download_data" and not provenance:
        return {"ok": False, "stage": "fetch",
                "error": "experimento download_data sin datos descargables verificables"}

    # for gz files the analysis reads the DECOMPRESSED sibling — preview + SCHEMA
    previews = {}
    for d in provenance:
        readable = d.get("decompressed_to") or d["filename"]
        previews[readable] = _head_preview(data_dir / readable)
        sch = _schema(data_dir / readable)   # REAL columns + row count for codegen
        if sch:
            d["columns"], d["n_rows"] = sch["columns"], sch["n_rows"]
            d["fmt"] = sch.get("delimiter")

    # 3-4) codegen + sandboxed run + repair loop
    runner = SubprocessRunner()

    def _one_impl(extra: str | None) -> tuple[dict[str, Any] | None, str, Any, int, str]:
        feedback = extra
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
                return None, "", None, attempts, f"codegen: {str(exc)[:250]}"
            sres = runner.run(code, workdir, timeout_sec=SANDBOX_TIMEOUT,
                              memory_mb=SANDBOX_MEMORY_MB,
                              cpu_seconds=SANDBOX_TIMEOUT, allow_network=False)
            if sres.status == "ok" and sres.exit_code == 0:
                result, why = _parse_result(sres.stdout)
                if result is not None:
                    return result, code, sres, attempts, ""
            feedback = ((extra + "\n\n") if extra else "") + (
                f"status={sres.status} exit={sres.exit_code}\n"
                f"STDERR:\n{(sres.stderr or '')[-1200:]}\n"
                f"STDOUT (cola):\n{(sres.stdout or '')[-600:]}\n"
                + (f"VALIDACIÓN: {why}" if why else ""))
            result = None
        return None, code, sres, attempts, feedback or "sin resultado válido"

    result, code, sres, attempts, err = _one_impl(None)
    if result is None:
        (workdir / "last_attempt.py").write_text(code or "", encoding="utf-8")
        return {"ok": False, "stage": "run", "attempts": attempts,
                "error": err[:400]}

    # 4b) cross-check: a "supports" needs an INDEPENDENT second implementation
    cross_check: dict[str, Any] | None = None
    if verify_supports and result.get("verdict") == "supports":
        r2, code2, _s2, att2, err2 = _one_impl(_SECOND_IMPL)
        if r2 is None:
            cross_check = {"performed": True, "agreed": False,
                           "reason": f"2ª implementación no corrió: {err2[:200]}"}
        else:
            (workdir / "script_v2.py").write_text(code2, encoding="utf-8")
            agreed, detail = _compare_results(result, r2)
            cross_check = {"performed": True, "agreed": agreed, "detail": detail,
                           "second_verdict": r2.get("verdict"),
                           "attempts": att2}
        if not cross_check.get("agreed"):
            result["verdict"] = "inconclusive"
            result["verdict_reason"] = (
                "[degradado por ACERO: la verificación cruzada con una "
                "implementación independiente NO coincidió — "
                f"{cross_check.get('reason') or cross_check.get('detail','')}] "
                + str(result.get("verdict_reason", "")))[:400]

    # figures written by the script (if any)
    out_dir = workdir / "out"
    result["figures"] = sorted(f.name for f in out_dir.glob("*.png")) \
        if out_dir.exists() else []

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

    # storage policy: big raw data files are PRUNED after a successful run —
    # they are re-fetchable (URL + sha256 live in provenance.json) and one
    # deduplicated copy stays in the shared cache (LRU-capped). Script, result,
    # provenance and stdout (all tiny) are kept forever.
    if os.environ.get("ACERO_KEEP_DATA") != "1":
        for pv in provenance:
            fp = data_dir / pv["filename"]
            if fp.exists() and fp.stat().st_size > PRUNE_DATA_OVER_BYTES:
                fp.unlink()
                pv["pruned"] = True
    _enforce_cache_cap()

    return {"ok": True, "result": result, "provenance": provenance,
            "attempts": attempts, "cross_check": cross_check,
            "code_path": str(workdir / "script.py"),
            "artifacts_dir": str(workdir),
            "duration_sec": round(getattr(sres, "duration_sec", 0.0), 2),
            "generator": "codex+sandbox",
            "disclaimer": ("Análisis con CÓDIGO GENERADO POR IA ejecutado en sandbox "
                           "sobre datos con procedencia verificada. Candidato a "
                           "revisión humana del código; no es un descubrimiento.")}
