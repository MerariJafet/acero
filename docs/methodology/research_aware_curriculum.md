# Methodology — Research-Aware Curriculum

Curricula are DERIVED from real investigations, not from a generic syllabus. For each
project ACERO emits `ResearchLearningRequirement`s tying a concept to the equations, code,
and assumptions that make it matter, with a criticality and a required mastery level.

Example (SINDy inference): derivative_estimation, regularization, collinearity,
identifiability, imposed_library, noise, extrapolation, governing_structure — each anchored
to a real file (e.g. `inference/discovery/sparse_identification.py`) and a real caveat
("derivatives from same data", "library is polynomial").

## Prerequisite graph
`curriculum/concept_graph.py` supports relation kinds (requires, *_depends_on,
helps_understand, is_example_of, generalizes) and detects missing prerequisites, invalid
cycles, minimum learning paths, foundational concepts, redundant dependencies, and
alternative routes. Hard prerequisites (requires / *_depends_on) drive sequencing; soft
links inform without gating.
