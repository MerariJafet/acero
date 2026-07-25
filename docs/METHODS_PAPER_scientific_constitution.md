# A Computable Scientific Constitution for Autonomous Data-Driven Research

**Draft methodological paper — candidate for preprint, pending human review.**
*The AI system is a tool, never an author. This draft was prepared with AI assistance
under human direction; all scientific claims require independent human validation.*

---

## Resumen (ES)

Los sistemas de investigación basados en modelos de lenguaje pueden producir texto
científico plausible sin una cadena de evidencia suficientemente fuerte. Presentamos una
**constitución científica computable**: un conjunto de reglas ejecutables que separan por
código el descubrimiento de la confirmación, contabilizan todo el espacio de búsqueda,
hacen explícitas las hipótesis causales, gradúan la independencia de la evidencia y acotan
la afirmación que un resultado puede hacer. En un benchmark de ablación, la constitución
reduce la tasa de falsos positivos de **100 % a 0 %** sobre casos indefendibles conocidos,
sin bloquear casos válidos. El sistema se detiene deliberadamente en el estado "candidato a
revisión humana" y nunca declara un descubrimiento.

## Abstract (EN)

Language-model-based research systems can generate plausible scientific text without a
sufficiently strong evidential chain. We present a **computable scientific constitution**:
a set of executable rules that (i) separate discovery from confirmation, (ii) account for
the entire search space, (iii) make causal assumptions explicit and refuse causal language
when a claim is not identifiable, (iv) grade the independence of evidence, and (v) compile
the maximum claim a result is allowed to make. In an ablation benchmark over known
indefensible cases, the constitution reduces the false-positive rate from **100 % to 0 %**
without blocking defensible cases. The system deliberately halts at a "candidate for human
review" state and never declares a discovery. All governance logic is deterministic and
unit-tested.

---

## 1. The problem

Autonomous, LLM-driven pipelines are prone to a specific failure: they optimize for
producing *a result*. Given the freedom to explore data, repair code, try subsets, and
reinterpret findings, such a system can surface a "significant" pattern that arose from
opportunistic exploration, confounding, information leakage, hidden dependence between
analyses, or self-serving narrative revision (semantic HARKing). Good scientific
*principles* are insufficient; what is needed is *governance that can prevent
epistemically invalid actions even when the agent would take them*.

## 2. Design principles (invariants)

1. **An LLM is never evidence.** Evidence comes from auditable code over identifiable data.
2. **Nothing is a discovery** without expert human review and independent replication.
3. **Full provenance** for every datum (URL + bytes + SHA-256).
4. **Negatives are preserved**; a result without a null test degrades to inconclusive.
5. **Re-execution ≠ replication**; the two are distinct, tracked states.
6. **The system cannot publish, declare a finding, or approve itself.**
7. **Every claim is bounded** by design, estimand, evidence and assumptions.

## 3. The constitution

Each component is an executable module (`src/acero/science/`), deterministic and
unit-tested.

- **Two regimes + pre-registration.** Discovery is free; confirmation requires a
  **frozen analysis plan** (hypothesis, primary variable, population, criteria, transform,
  model, primary test, multiplicity correction, minimum effect, decision rule, failure
  conditions) hashed over its *scientific content* (so post-hoc edits are detectable).
  Confirmatory data cannot be unblinded without a frozen protocol. Seal levels grade the
  proof of anteriority (local hash → external timestamp → public preregistration).
- **Search-space ledger.** Records every researcher degree of freedom across the whole
  mission (hypotheses, columns, subsets, transforms, models, seeds, exclusions) and
  computes an *exploration debt*. Any decision made after seeing the data is exploratory by
  construction.
- **Semantic exploration ledger + hypothesis lineage.** Captures the search that happens
  *before code* (questions, discarded hypotheses, rejected datasets, endpoint/
  interpretation/title changes). A result-sensitive change made after seeing results is
  flagged as HARKing and forbids confirmatory classification without new independent
  evidence.
- **Sealed holdout.** Deterministic random/temporal/group splits; the holdout is locked
  until an unblinding event. Group splits keep whole entities on one side (anti-leakage).
- **Causal layer (CAUSA).** An explicit estimand and DAG; Pearl's back-door criterion via
  d-separation; collider/mediator detection. Each edge carries evidence (assumed /
  literature / experimental / expert-approved). A DAG whose edges are merely
  LLM-proposed can be syntactically valid and identifiable but is **never** substantively
  validated, and strong causal language is refused.
- **Independence graph.** Independence between datasets is *computed* from provenance
  (study, assay/source, laboratory, cohort, instrument, curation pipeline, provenance
  root), not declared. A split of the same dataset is `SAME_PARTITION` and can never count
  as independent replication; sharing a curation root degrades to `SAME_STUDY`.
- **Independence levels (0–6) + claim compiler.** A second implementation is not
  independence. The claim compiler maps evidence to the maximum permitted claim
  (associated / predicts / effect-under-assumptions / replicated) and lints a draft for
  language that exceeds it (*demonstrates, proves, causes, discovery*).
- **Structure-preserving null catalog.** Recommends the valid null family from the data
  structure and warns when a plain label permutation would inflate false positives.
- **Simulation & recovery bench.** Synthetic universes with known truth measure false-
  positive rate, power, bias, and expose when a method is fooled by confounding or leakage.
- **Contribution score + uncertainty budget.** Four novelty types (bibliographic / data /
  methodological / scientific); "not found" ≠ "new". A multidimensional uncertainty budget
  replaces a single confidence number.
- **Plural adversarial panel.** Eight reviewers with incompatible mandates (statistician,
  causalist, domain expert, replicator, data detective, novelty reviewer, alternative-
  mechanism advocate, hostile writer). Disagreement is preserved; a hard-mandate block
  halts advancement.
- **State machine.** IDEA → … → CANDIDATE_FOR_PREPRINT (**system ceiling**) → peer review
  → published → externally replicated (last three: external agents only).

## 4. Evaluation

### 4.1 Ablation: does governance reduce false positives?

Nine positive results with known flaws (causal over-claim, no null test, high exploration
debt, confounding, leakage, missing controls, false novelty) and two genuinely clean cases
were judged by two pipelines: a naive pipeline (reports any positive) and the constitution.

| | Without constitution | With constitution |
|---|---:|---:|
| False positives (of 7 indefensible) | 7 | **0** |
| False-positive rate | 100 % | **0 %** |
| False negatives (clean cases blocked) | — | **0** |

The constitution eliminates the indefensible positives while advancing the defensible
ones. (Reproducible: `acero science integrity`.)

### 4.2 Method-validation study under the confirmation regime (real data)

On 910 real molecules (Caco-2 permeability, Therapeutics Data Commons, fetched with a
SHA-256 manifest), we tested whether molecular polarity predicts lower permeability. In the
discovery split (n=619) the effect was +0.746 logP_app (t=13.1). We then **froze the
protocol** and only afterwards unblinded the sealed holdout (n=291): +0.769 (t=9.53), same
direction under the frozen decision rule → state `CONFIRMED_IN_HOLDOUT`. This recovers a
*known* pharmacological relationship (Veber's rule); its value is methodological — it shows
the system does not inflate an exploratory result to "confirmed" without a sealed holdout.

### 4.3 Independence is enforced, not assumed

A replication attempt on an independent assay (PAMPA, n=2035, artificial-membrane
permeability) reproduced the direction (z=6.92). The independence graph nonetheless
classified the pair as `SAME_STUDY` (shared TDC curation root) and **refused** to call it
independent replication. The system recorded cross-assay robustness without over-claiming.

### 4.4 The plural panel in practice

Run live (via an LLM) over the study above, the eight-voice panel produced genuinely
distinct critiques: the causalist blocked on uncontrolled confounding (molecular weight,
lipophilicity), the data detective flagged possible leakage from salts/tautomers across the
split, and the novelty reviewer marked the relationship as non-novel. The aggregate was "in
dispute", blocked by a hard mandate — stricter than a single critic.

## 5. Limitations

- The confirmation study recovers a *known* relationship; the system has not yet produced a
  *new*, externally replicated finding.
- The holdout used is a partition of the same dataset; genuine external replication requires
  a dataset from a different curation root (a discovery + harmonization problem, addressed
  by a replication-source finder, not yet fully closed for this case).
- The plural panel has been exercised on few missions; its blocking thresholds are not yet
  empirically calibrated.
- Distinguishing "genuinely unexplored" from "published but unindexed" remains hard.
- Self-evaluation is not independent; external methodological review is invited.

## 6. Availability

All governance logic is deterministic and unit-tested (110+ tests). CLI entry points:
`acero science integrity | states | simbench | independence | find-replication | demo`.
The scientific-constitution package is released as open source.

## 7. Ethics & authorship

The AI system is a tool, never an author (CRediT). It cannot publish or declare findings.
Its ceiling is `CANDIDATE_FOR_PREPRINT`; all subsequent states require external human
agents. Negative and inconclusive results are preserved by design.
