"""Full-text retrieval — download OPEN-ACCESS PDFs and extract their text.

Until now the agent read ABSTRACTS. This downloads the actual open-access PDF
(from OpenAlex/arXiv oa_url), verifies it is a PDF, extracts the text with pypdf,
and returns a real excerpt so the confrontation can read BEYOND the abstract.
Everything is best-effort and honest: a paper with no reachable OA PDF is simply
reported as abstract-only — never faked. PDFs are cached (by URL hash) and saved
to the project's Obsidian vault (Literatura/PDFs) for NotebookLM / manual reading.
"""

from __future__ import annotations

import hashlib
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

MAX_PDF_BYTES = 40 * 1024 * 1024        # 40 MB per PDF
FETCH_TIMEOUT = 90.0
MAX_PAGES = 40                          # cap extraction cost
_UA = "ACERO-fulltext/0.1 (+https://github.com/MerariJafet/acero)"


def _cache_dir() -> Path:
    env = os.environ.get("ACERO_EXPERIMENT_ARTIFACTS", "").strip()
    root = Path(env).parent if env else Path.home() / ".acero"
    d = root / "pdf_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_pdf(url: str, *, timeout: float = FETCH_TIMEOUT,
                 max_bytes: int = MAX_PDF_BYTES) -> bytes | None:
    """Download a PDF over HTTPS (cached by URL). Returns bytes or None."""
    if not url or not url.lower().startswith("https://"):
        return None
    ckey = _cache_dir() / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".pdf")
    if ckey.exists() and ckey.stat().st_size > 0:
        return ckey.read_bytes()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                                   "Accept": "application/pdf,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(max_bytes + 1)
    except Exception:  # noqa: BLE001 - a missing PDF is not an error, just absent
        return None
    if len(data) > max_bytes or data[:5] != b"%PDF-":
        return None
    ckey.write_bytes(data)
    return data


def extract_text(pdf_bytes: bytes, *, max_pages: int = MAX_PAGES) -> str:
    """Extract text from PDF bytes with pypdf. Empty string on failure."""
    try:
        import io

        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages[:max_pages]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                continue
        text = re.sub(r"\s+\n", "\n", "\n".join(parts))
        return re.sub(r"[ \t]{2,}", " ", text).strip()
    except Exception:  # noqa: BLE001
        return ""


def fetch_fulltext(paper: dict[str, Any], *,
                   downloader: Any | None = None,
                   extractor: Any | None = None) -> dict[str, Any]:
    """Best-effort: return {ok, chars, excerpt, pdf_bytes?, url} for one paper."""
    dl = downloader or download_pdf
    ex = extractor or extract_text
    url = (paper.get("pdf_url") or paper.get("oa_url") or "").strip()
    if not url and (paper.get("source") == "arxiv"):
        aid = (paper.get("url") or "").rsplit("/abs/", 1)[-1]
        if aid:
            url = f"https://arxiv.org/pdf/{aid}"
    if not url:
        return {"ok": False, "reason": "sin PDF open-access", "chars": 0}
    data = dl(url)
    if not data:
        return {"ok": False, "reason": "PDF no accesible", "chars": 0, "url": url}
    text = ex(data)
    if len(text) < 500:
        return {"ok": False, "reason": "texto no extraíble (PDF escaneado?)",
                "chars": len(text), "url": url}
    return {"ok": True, "chars": len(text), "url": url, "pdf_bytes": data,
            "excerpt": text[:6000], "fulltext": text}
