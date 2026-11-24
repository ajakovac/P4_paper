# Change log: LLM proposer envelope v02 / P0 v13

Conceptual change explicitly approved before construction of this package:
replace base P0 v12 by a task-agnostic consolidated P0 v13 matching the accepted
DP-v05 runtime behavior, while leaving the TAEP, task inputs, and KS snapshots
unchanged.

Changes:
1. Active formal P0 is `P0_consolidated_T1_T6_v13.tex`.
2. Transition output protocol is `LML_PROPOSER_TRANSITION_V02`.
3. Output schema adds a generic `construction_phase` serialization.
4. Invocation uses `CONSTRUCTION_CONTROL = enabled|disabled`.
5. Minimal result/trace views report construction status and dependent solution.
6. Added T5/T6-pre/T6-post convenience launchers.

Unchanged:
- TAEP bytes and approved SHA-256;
- all task DSPL files;
- KS0--KS9 snapshot bytes;
- Codex model/configuration and isolation policy;
- health-test logic;
- no expected answer or task-specific semantic prompt is added.
