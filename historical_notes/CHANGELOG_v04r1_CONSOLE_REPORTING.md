# v04r1 console-reporting adjustment

Scope: reporting only. No scientific input, proposer semantics, output schema,
P0, TAEP, task, KS, model configuration, or construction control was changed.

Changes:
- makes the obtained solution prominent in a separated console block;
- prints the selected rule/procedure directly below the solution;
- for bounded construction (notably T5), prints a compact description of the
  constructed procedure and its represented supporting schema/relation set;
- reports `no_local_solution -> construction entered` for a successful
  construction episode instead of leaving the visually prominent phrase
  `no local candidates` without context;
- keeps the full local-search information in `MINIMAL_TRACE.txt` and the full
  structured result in `TRANSITION_OUTPUT.json`.

The distinction remains explicit: T5 has `local_outcome=no_local_solution`
while the complete transition has a dependent solution produced after bounded
construction.
