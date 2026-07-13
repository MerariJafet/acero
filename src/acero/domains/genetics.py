"""Genetics domain plugin — computational sequence analysis and population genetics.

STRICTLY computational: sequence math, transcription/translation tables, and
Hardy-Weinberg. NO wet-lab, NO organism/pathogen design, NO protocols. The
research_safety policy forbids the dangerous domains outright.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import BenchmarkCase, BenchmarkResult, DomainPlugin, ValidationResult

DNA_ALPHABET = set("ACGT")
RNA_ALPHABET = set("ACGU")

# Standard genetic code (RNA codons -> amino acid single-letter; '*' = stop).
CODON_TABLE = {
    "UUU": "F", "UUC": "F", "UUA": "L", "UUG": "L",
    "CUU": "L", "CUC": "L", "CUA": "L", "CUG": "L",
    "AUU": "I", "AUC": "I", "AUA": "I", "AUG": "M",
    "GUU": "V", "GUC": "V", "GUA": "V", "GUG": "V",
    "UCU": "S", "UCC": "S", "UCA": "S", "UCG": "S",
    "CCU": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACU": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCU": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "UAU": "Y", "UAC": "Y", "UAA": "*", "UAG": "*",
    "CAU": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAU": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAU": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "UGU": "C", "UGC": "C", "UGA": "*", "UGG": "W",
    "CGU": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGU": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGU": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


class GeneticsPlugin(DomainPlugin):
    name = "genetics"
    domain = "genetics"
    units = {"sequence": "nucleotides", "frequency": "fraction[0,1]"}
    allowed_tools = ["gc_content", "transcribe", "translate", "hardy_weinberg"]
    risks = [
        "Solo análisis computacional de secuencias; sin laboratorio húmedo.",
        "Prohibido diseño de organismos/patógenos/toxinas (research_safety).",
        "Modelos poblacionales idealizados (apareamiento aleatorio, sin selección).",
    ]

    def _simulators(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "gc_content": self._gc_content,
            "transcribe": self._transcribe,
            "translate": self._translate,
            "hardy_weinberg": self._hardy_weinberg,
        }

    def _gc_content(self, p: dict[str, Any]) -> dict[str, Any]:
        seq = str(p["sequence"]).upper()
        if not seq:
            return {"gc_content": 0.0}
        gc = sum(1 for b in seq if b in ("G", "C"))
        return {"gc_content": gc / len(seq)}

    def _transcribe(self, p: dict[str, Any]) -> dict[str, Any]:
        dna = str(p["sequence"]).upper()
        return {"rna": dna.replace("T", "U")}

    def _translate(self, p: dict[str, Any]) -> dict[str, Any]:
        seq = str(p["sequence"]).upper()
        rna = seq.replace("T", "U")
        protein = []
        for i in range(0, len(rna) - len(rna) % 3, 3):
            aa = CODON_TABLE.get(rna[i:i + 3], "X")
            if aa == "*":
                break
            protein.append(aa)
        return {"protein": "".join(protein)}

    def _hardy_weinberg(self, p: dict[str, Any]) -> dict[str, Any]:
        pa = float(p["p"])
        qa = 1.0 - pa
        return {"AA": pa ** 2, "Aa": 2 * pa * qa, "aa": qa ** 2}

    def validate(self, kind: str, data: dict[str, Any]) -> ValidationResult:
        if kind in ("dna", "sequence") and "sequence" in data:
            seq = str(data["sequence"]).upper()
            alphabet = RNA_ALPHABET if kind == "rna" else DNA_ALPHABET
            bad = set(seq) - alphabet
            if bad:
                return ValidationResult.invalid(
                    "sequence", f"invalid nucleotides {sorted(bad)}; allowed {sorted(alphabet)}"
                )
        if kind == "allele_freq" and "p" in data:
            if not 0.0 <= float(data["p"]) <= 1.0:
                return ValidationResult.invalid("p", "allele frequency must be in [0, 1]")
        return ValidationResult.valid()

    def project_template(self) -> str:
        return (
            "# Proyecto de Genética Computacional\n\n"
            "- Pregunta:\n- Secuencias/datos (fuente pública + licencia):\n"
            "- Hipótesis competidoras:\n- Herramientas: gc_content | transcribe | "
            "translate | hardy_weinberg\n- Supuestos poblacionales:\n"
            "- NOTA: sin laboratorio húmedo; solo cómputo.\n"
        )

    def benchmark(self) -> BenchmarkResult:
        cases: list[BenchmarkCase] = []
        gc = self._gc_content({"sequence": "GGCCATAT"})["gc_content"]  # 4/8
        cases.append(BenchmarkCase("gc_content_half", 0.5, gc, 1e-9))
        hw = self._hardy_weinberg({"p": 0.6})
        cases.append(BenchmarkCase("hw_AA", 0.36, hw["AA"], 1e-9))
        cases.append(BenchmarkCase("hw_Aa", 0.48, hw["Aa"], 1e-9))
        cases.append(BenchmarkCase("hw_aa", 0.16, hw["aa"], 1e-9))
        # AUG AAA -> M K ; TAA stop; start codon translates to Methionine
        prot_len = len(self._translate({"sequence": "ATGAAATAA"})["protein"])
        cases.append(BenchmarkCase("translate_len_MK", 2.0, float(prot_len), 0))
        return BenchmarkResult(domain=self.domain, cases=cases)
