"""Verification packet — how a claim leaves ACERO to be checked by someone else.

Exporting was local-only and there was no way for a third party to verify anything
without trusting us. This builds a SELF-CONTAINED, offline-verifiable folder (and
optional .zip) that you hand to a reviewer:

    packet/
      manifest.json        the ReviewBundle: every file + its sha256, AI disclosure
      verify.py            stdlib-only checker: recomputes hashes, prints a verdict
      VERIFY.md            what this is, how to check it, what the states mean
      attestation.json     template the reviewer fills in and returns
      files/…              the actual artifacts (script, result, provenance, data hashes)

The reviewer runs `python verify.py` — no install, no network, no ACERO — and gets
INTACT or TAMPERED, plus the manifest hash. They fill `attestation.json` and send it
back; `publication.external_validation.record_attestation` ingests it and only then
can readiness reach EXTERNALLY_VALIDATED.

ACERO still never auto-publishes: this produces a FILE that the human decides to
share. The packet asserts integrity + reproducibility, never "discovery".
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..reproduction.bundle import ReviewBundle, build_bundle

VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""Offline verifier for an ACERO verification packet. Stdlib only, no network.

Usage:  python verify.py            (run from inside the packet folder)
Exit 0 = INTACT, 1 = TAMPERED/INCOMPLETE.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_hash(m):
    d = {k: v for k, v in m.items() if k != "signature"}
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    man = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    files = man.get("files", {})
    missing, modified = [], []
    for name, recorded in files.items():
        p = HERE / "files" / name
        if not p.is_file():
            missing.append(name)
        elif sha256(p) != recorded:
            modified.append(name)
    mh = manifest_hash(man)
    print("ACERO verification packet")
    print("  title      :", man.get("title"))
    print("  version    :", man.get("version"), "commit:", man.get("commit"))
    print("  files      :", len(files), "checked")
    print("  manifest   :", mh)
    if missing or modified:
        print("  VERDICT    : TAMPERED / INCOMPLETE")
        for n in missing:
            print("    missing :", n)
        for n in modified:
            print("    modified:", n)
        return 1
    print("  VERDICT    : INTACT (hashes match the manifest)")
    print()
    print("NOTE: INTACT proves the artifacts are unmodified. It does NOT by itself")
    print("prove the science. To attest reproduction, re-run the analysis script in")
    print("files/ and compare the result, then fill attestation.json.")
    print("Put this manifest hash in attestation.json -> bundle_hash:")
    print("  ", mh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

VERIFY_MD = """# Paquete de verificación ACERO — {title}

Este paquete existe para que **puedas comprobarlo tú, sin confiar en nosotros**.
No requiere instalar nada, ni red, ni ACERO.

## 1. Verificar integridad (10 segundos)

```bash
python verify.py
```

- `INTACT` → los archivos coinciden exactamente con el manifiesto (nadie los alteró).
- `TAMPERED / INCOMPLETE` → algo cambió; el paquete no es de fiar.

## 2. Reproducir el análisis (lo que de verdad importa)

Integridad ≠ ciencia. Para atestiguar reproducción, vuelve a ejecutar el script de
análisis incluido en `files/` con los datos indicados en la procedencia y compara
el resultado con el registrado.

## 3. Devolver tu attestation

Rellena `attestation.json` y envíasela al autor:

- `validator`, `affiliation`, `contact` — quién eres (debe ser una persona).
- `independent` — declara que no tienes conflicto de interés con el autor.
- `bundle_hash` — el hash de manifiesto que imprimió `verify.py`.
- `verdict` — `reproduced` | `partial` | `failed` (los negativos también valen y se
  conservan).
- `notes` — qué hiciste y qué viste.

Solo con reproducciones **independientes** el trabajo puede alcanzar el nivel
`EXTERNALLY_VALIDATED`. Si el contenido cambia después, tu attestation se marca
obsoleta y deja de contar.

## Declaración de uso de IA

{ai_disclosure}

## Qué NO afirma este paquete

No afirma un descubrimiento. El techo de ACERO es *listo para revisión científica
humana*; la autoría y la conclusión son del investigador humano.

Generado: {generated_at}
"""


def manifest_hash(bundle: ReviewBundle) -> str:
    """Stable hash of the manifest — the anchor an attestation binds to."""
    return hashlib.sha256(bundle.manifest_bytes()).hexdigest()


def build_packet(source_dir: str | Path, dest: str | Path, *, title: str,
                 version: str = "", commit: str = "",
                 ai_disclosure: str = ("Análisis asistido por IA; el código fue escrito "
                                       "por un modelo y revisado por el investigador "
                                       "humano, que es el autor y la autoridad final."),
                 review_questions: list[str] | None = None,
                 include: list[str] | None = None,
                 make_zip: bool = False) -> dict[str, Any]:
    """Assemble the packet. Returns {path, manifest_hash, files, zip?}."""
    src = Path(source_dir).resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"source_dir no existe: {src}")
    out = Path(dest).resolve()
    (out / "files").mkdir(parents=True, exist_ok=True)

    names = include or [p.name for p in sorted(src.iterdir()) if p.is_file()]
    for name in names:
        p = src / name
        if p.is_file():
            shutil.copy2(p, out / "files" / name)

    bundle = build_bundle(out / "files", title=title, version=version, commit=commit,
                          ai_disclosure=ai_disclosure,
                          review_questions=review_questions or [
                              "¿La afirmación central está respaldada por la evidencia?",
                              "¿Los controles nulos son adecuados?",
                              "¿Reproduces el resultado con los datos indicados?"])
    mh = manifest_hash(bundle)

    (out / "manifest.json").write_text(
        json.dumps(bundle.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "verify.py").write_text(VERIFY_SCRIPT, encoding="utf-8")
    (out / "VERIFY.md").write_text(
        VERIFY_MD.format(title=title, ai_disclosure=ai_disclosure,
                         generated_at=now_iso()), encoding="utf-8")
    (out / "attestation.json").write_text(json.dumps({
        "validator": "", "affiliation": "", "contact": "",
        "independent": True, "bundle_hash": mh,
        "verdict": "reproduced | partial | failed", "notes": "",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    result: dict[str, Any] = {"path": str(out), "manifest_hash": mh,
                              "files": len(bundle.files), "title": title}
    if make_zip:
        zip_base = str(out)
        result["zip"] = shutil.make_archive(zip_base, "zip", root_dir=str(out))
    return result


def read_attestation(path: str | Path) -> dict[str, Any]:
    """Load a returned attestation.json (still unvalidated — the caller records it)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
