# Human Understanding Engine (Sprint 9)

Keeps the human researcher intellectually inside the loop. It is not a chatbot tutor or a
linear course: it observes a REAL ACERO investigation and works out what the researcher
must understand, what they already understand, what they *think* they understand but
confuse, and what they must learn before approving a conclusion — measured by performance,
never by "yes, I get it" or by a Codex explanation.

## Package `src/acero/understanding/`
- **learner/** — `knowledge_state` (evidence-gated state machine UNKNOWN→…→MASTERED),
  `misconceptions` (12 canonical confusions, negation-aware), `confidence` (human
  calibration via the inference calibration primitives), `history` (append-only log +
  spaced review).
- **curriculum/** — `concept_graph` (prerequisites, cycles, minimum path, foundational
  concepts, redundant edges) and `research_curriculum` (requirements DERIVED from real
  investigations: SINDy, analogy, sunspots).
- **explanation/** — `levels` builds five distinct artifacts (intuition, conceptual,
  mathematical, computational, frontier), every one carrying its limitations; `explain_mode`
  answers EXPLAIN_* queries (abstention must give a concrete cause).
- **assessment/** — `grading` (rubric coverage, partial credit, keyword-echo guard),
  `predictions` (lock-after-reveal), `exercises` (solution withheld until attempt),
  `transfer` (cross-domain), `questions` (Bloom levels).
- **intervention/** — `comprehension_gate` (blocks critical decisions below the required
  level; traceable human override), `socratic` (questions validated against real project
  entities), `reflection`.
- **engine.py** — orchestrator; every research action yields a `ScientificUpdate` AND a
  `HumanUnderstandingUpdate`.
- **store.py** — persistence over the generic `discovery` table.
- **audit/** — adversarial pedagogical audit (rules + real Codex).
- **dashboard.py** — a first functional HTML dashboard.

## The knowledge-state machine
States are a real ladder; each rung requires a DIFFERENT kind of performance evidence.
MASTERED additionally requires ≥4 distinct evidence kinds, so a single correct answer can
never grant mastery. A detected misconception forces MISCONCEIVED until resolved by NEW
contradicting evidence. Self-reported confidence is recorded but never advances state on
its own; the gap to observed ability is surfaced as overconfidence.

## Honesty
"Mastery" here means *demonstrated performance across several task types on the concepts a
decision depends on* — not perfect understanding. Grading is deterministic keyword/element
coverage: it can miss nuance and can be gamed by verbose wrong answers; that is why (a)
multiple distinct evidence kinds are required, (b) forbidden claims are penalised, (c)
keyword-echo is flagged, and (d) Codex is advisory only. A passed assessment is evidence,
not proof, of understanding.
