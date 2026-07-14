# Applicability Regimes

Every concept states where it applies and where it breaks: spatial/temporal/energy
scales, parameter ranges, assumptions, valid and invalid conditions, and evidence.
Examples: classical mechanics (breaks at relativistic speeds / quantum scales), ideal
gas (breaks at high density / low temperature), small-angle pendulum (breaks at large
amplitude), Hardy-Weinberg (breaks under selection/migration/drift). `is_applicable`
returns False when a condition matches an invalid regime, and the engine can answer
"in what regime does this representation break down?" and "what theory generalises
it?".
